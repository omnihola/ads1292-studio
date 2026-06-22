"""Acquisition controller for the Qt front-end.

Owns the reused :class:`LiveWorker`, the inter-thread queues, and the
connect/start/stop/calibrate/load logic. UI code calls these methods and polls
:meth:`drain_results` / :meth:`drain_samples` from a QTimer — the exact
queue-drain pattern proven in the Tk app, so the threading model is unchanged.

On Stop (once the CSV writer thread ends) a recording is finalized into the
same three artifacts the Tk app produces: the raw CSV (written live by the
worker), a JSON bundle (``write_recording_bundle``), and an ``.xlsx``
(``write_recording_xlsx``).
"""
from __future__ import annotations

import os
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ads1292_studio.acquisition import (
    build_acquisition_provenance,
    finalize_acquisition_provenance,
)
from ads1292_studio.calibration import Calibration, LiveStreamCalibration
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.device import Ads1x9xDevice
from ads1292_studio.events import EventMarker
from ads1292_studio.gui_state import GuiState
from ads1292_studio.gui_workers import ConnectResult, CsvLoadResult, LiveCalibrationResult
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.models import Recording, StreamSample, StreamStartResult
from ads1292_studio.processing import build_processing_settings
from ads1292_studio.protocol import protocol_template
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.h5_io import is_recording_h5_path, read_recording_h5, write_recording_h5
from ads1292_studio.recording_paths import recording_csv_path
from ads1292_studio.xlsx_io import write_recording_xlsx
from ads1292_studio.workers import AcquisitionMode, LiveWorker

MAX_SAMPLES_PER_DRAIN = 1000
SAMPLE_RATE_HZ = 500.0


def _fsync_path(path: Path) -> None:
    """Force a written file to durable storage (best-effort)."""
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


@dataclass
class DrainOutcome:
    """Side effects produced by draining the queues during one tick."""

    logs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    state_changed: bool = False
    loaded_recording: Recording | None = None


class AcquisitionController:
    def __init__(self) -> None:
        self.samples: queue.Queue[StreamSample] = queue.Queue()
        self.logs: queue.Queue[str] = queue.Queue()
        self.connect_results: queue.Queue[ConnectResult] = queue.Queue()
        self.stream_start_results: queue.Queue[StreamStartResult] = queue.Queue()
        self.csv_load_results: queue.Queue[CsvLoadResult] = queue.Queue()
        self.calibration_results: queue.Queue[LiveCalibrationResult] = queue.Queue()
        self.worker = LiveWorker(self.samples, self.logs, self.stream_start_results)

        self.connected_port: str | None = None
        self.selected_port: str = ""
        self.recording_path: Path | None = None
        self.is_connecting = False
        self.is_starting = False
        self.is_streaming = False
        self.is_loading_csv = False
        self.is_calibrating_live = False
        self.has_data = False
        self.live_calibration: LiveStreamCalibration | None = None
        self.loaded_samples: tuple = ()
        self.loaded_csv_path: Path | None = None

        self._finalization_pending = False
        self._record_metadata = SessionMetadata()
        self._record_quality_gate = QualityGate()
        self._record_protocol = protocol_template()
        self._record_provenance = None
        self._record_started_iso = ""
        # selected output formats (CSV journal is always written live; these
        # decide what is kept/produced at finalize)
        self._keep_csv = True
        self._save_h5 = True
        self._save_xlsx = False
        self.event_markers: list[EventMarker] = []

    # ---- state snapshot (drives the whole UI via gui_state) ----
    def snapshot(self) -> GuiState:
        return GuiState(
            connected=self.connected_port is not None,
            streaming=self.is_streaming,
            has_data=self.has_data,
            has_recording_path=self.recording_path is not None,
            has_port=bool(self.selected_port.strip()),
            selected_port=self.selected_port,
            loading_csv=self.is_loading_csv,
            connecting=self.is_connecting,
            starting=self.is_starting,
            calibrating_live=self.is_calibrating_live,
        )

    # ---- connect ----
    def connect(self, port: str) -> None:
        if self.is_connecting or not port:
            return
        self.selected_port = port
        self.is_connecting = True
        threading.Thread(target=self._connect_bg, args=(port,), daemon=True).start()

    def _connect_bg(self, port: str) -> None:
        try:
            with Ads1x9xDevice(port) as device:
                firmware = device.query_firmware()
            self.connect_results.put(ConnectResult(port=port, detail=f"firmware {firmware}"))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.connect_results.put(ConnectResult(port=port, error=str(exc)))

    # ---- live calibration ----
    def calibrate(self, port: str) -> None:
        if self.is_calibrating_live or self.connected_port != port or self.is_streaming:
            return
        self.is_calibrating_live = True
        threading.Thread(target=self._calibrate_bg, args=(port,), daemon=True).start()

    def _calibrate_bg(self, port: str) -> None:
        try:
            with Ads1x9xDevice(port, timeout=0.35) as device:
                calibration = device.run_live_stream_calibration(runs=5, seconds_per_run=4.0)
            self.calibration_results.put(LiveCalibrationResult(port=port, calibration=calibration))
        except Exception as exc:  # noqa: BLE001
            self.calibration_results.put(LiveCalibrationResult(port=port, error=str(exc)))

    # ---- start / stop ----
    def start(
        self,
        port: str,
        *,
        save_csv: bool,
        save_h5: bool = True,
        save_xlsx: bool = False,
        mode: AcquisitionMode = AcquisitionMode.LIVE,
        metadata: SessionMetadata | None = None,
        quality_gate: QualityGate | None = None,
        protocol=None,
    ) -> None:
        if self.connected_port != port or self.is_streaming:
            return
        # Never orphan a previous recording: if its finalize is still pending
        # (worker not yet drained), finalize it before resetting state.
        if self._finalization_pending:
            self.finalize_now()
        self.recording_path = None
        self._finalization_pending = False
        self.event_markers = []
        # CSV journal is the live, crash-safe source for finalize; it is written
        # whenever ANY format is requested, then kept or removed per save_csv.
        self._keep_csv = save_csv
        self._save_h5 = save_h5
        self._save_xlsx = save_xlsx
        record = save_csv or save_h5 or save_xlsx
        csv_path = None
        if record:
            started_at = datetime.now()
            self._record_started_iso = started_at.isoformat(timespec="seconds")
            csv_path = recording_csv_path(started_at=started_at, acquisition_mode=mode)
            self.recording_path = csv_path
            self._record_metadata = metadata or SessionMetadata()
            self._record_quality_gate = quality_gate or QualityGate()
            self._record_protocol = protocol or protocol_template()
            live_calibration = self.live_calibration if mode is AcquisitionMode.LIVE else None
            self._record_provenance = build_acquisition_provenance(
                csv_path=csv_path,
                acquisition_mode=mode.value,
                port=port,
                sample_rate_hz=SAMPLE_RATE_HZ,
                calibration=Calibration(),
                live_calibration=live_calibration,
                started_at=self._record_started_iso,
            )
            self._finalization_pending = True
        self.is_starting = True
        live_calibration = self.live_calibration if mode is AcquisitionMode.LIVE else None
        self.worker.start(port, csv_path, mode=mode, calibration=Calibration(), live_calibration=live_calibration)

    def stop(self) -> None:
        self.worker.stop()
        self.is_streaming = False

    # ---- load CSV (offline review) ----
    def load_csv(self, path: Path) -> None:
        if self.is_loading_csv:
            return
        self.is_loading_csv = True
        threading.Thread(target=self._load_csv_bg, args=(path,), daemon=True).start()

    def _load_csv_bg(self, path: Path) -> None:
        try:
            if is_recording_h5_path(path):
                recording, _ = read_recording_h5(path)
            else:
                recording = read_recording_csv(path)
            self.csv_load_results.put(CsvLoadResult(path=path, recording=recording))
        except Exception as exc:  # noqa: BLE001
            self.csv_load_results.put(CsvLoadResult(path=path, error=str(exc)))

    # ---- recording finalization (CSV + JSON bundle + XLSX) ----
    @property
    def has_pending_recording(self) -> bool:
        return self._finalization_pending

    def _worker_alive(self) -> bool:
        thread = getattr(self.worker, "thread", None)
        return bool(thread is not None and thread.is_alive())

    def finalize_now(self) -> DrainOutcome:
        """Stop the worker, wait for the CSV writer to flush, and finalize.

        Called on window close so a recording is never left CSV-only because the
        app exited before the per-tick finalizer ran.
        """
        out = DrainOutcome()
        self.worker.stop()
        self.is_streaming = False
        thread = getattr(self.worker, "thread", None)
        if thread is not None:
            thread.join(timeout=3.0)
        if self._finalization_pending:
            self._finalize_recording(out)
        return out

    def _finalize_recording(self, out: DrainOutcome) -> None:
        if self.recording_path is None or self._record_provenance is None:
            self._finalization_pending = False
            return
        try:
            recording = read_recording_csv(self.recording_path)
            samples = recording.samples
            sample_count = len(samples)
            first_ts = samples[0].timestamp if samples else 0.0
            last_ts = samples[-1].timestamp if samples else 0.0
            finalized = datetime.now().isoformat(timespec="seconds")
            provenance = finalize_acquisition_provenance(
                self._record_provenance,
                ended_at=finalized,
                finalized_at=finalized,
                sample_count=sample_count,
                first_timestamp_seconds=first_ts,
                last_timestamp_seconds=last_ts,
            )
            events = tuple(self.event_markers)
            out.logs.append(f"Recording finalized: {sample_count} samples")
            # Write the user-selected formats. The CSV journal is the live,
            # crash-safe source; it is removed only after a replacement format
            # was durably written (fsync'd), never leaving zero lossless copies.
            wrote_replacement = False
            if self._save_h5:
                h5_path = write_recording_h5(
                    self.recording_path,
                    samples=samples,
                    sample_rate_hz=SAMPLE_RATE_HZ,
                    metadata=self._record_metadata,
                    events=events,
                    calibration=Calibration(),
                    acquisition=provenance,
                    protocol=self._record_protocol,
                    quality_gate=self._record_quality_gate,
                    processing=build_processing_settings(sample_rate_hz=SAMPLE_RATE_HZ),
                    created_at=finalized,
                )
                _fsync_path(h5_path)
                wrote_replacement = True
                out.logs.append(f"Canonical HDF5 written: {h5_path}")
            if self._save_xlsx:
                xlsx_path = write_recording_xlsx(
                    self.recording_path, events=events, sample_rate_hz=SAMPLE_RATE_HZ
                )
                _fsync_path(xlsx_path)
                wrote_replacement = True
                out.logs.append(f"XLSX written (Events + Data tabs): {xlsx_path}")
            if self._keep_csv:
                out.logs.append(f"CSV journal kept: {self.recording_path}")
            elif wrote_replacement:
                self.recording_path.unlink(missing_ok=True)
                out.logs.append("CSV journal removed (not selected)")
            else:
                out.logs.append("CSV journal kept (no replacement format was written)")
        except Exception as exc:  # noqa: BLE001
            out.errors.append(f"Recording finalization failed: {exc}")
        finally:
            self._finalization_pending = False

    # ---- per-tick draining ----
    def drain_results(self) -> DrainOutcome:
        out = DrainOutcome()
        while True:
            try:
                out.logs.append(self.logs.get_nowait())
            except queue.Empty:
                break
        while True:
            try:
                res = self.connect_results.get_nowait()
            except queue.Empty:
                break
            self.is_connecting = False
            out.state_changed = True
            if res.error:
                self.connected_port = None
                out.errors.append(f"Connect failed: {res.error}")
            else:
                self.connected_port = res.port
                out.logs.append(f"Connected to {res.port}: {res.detail}")
        while True:
            try:
                res = self.stream_start_results.get_nowait()
            except queue.Empty:
                break
            self.is_starting = False
            out.state_changed = True
            if res.ok:
                self.is_streaming = True
            else:
                self.is_streaming = False
                out.errors.append(f"Start failed: {res.error or 'unknown error'}")
        while True:
            try:
                res = self.csv_load_results.get_nowait()
            except queue.Empty:
                break
            self.is_loading_csv = False
            out.state_changed = True
            if res.error or res.recording is None:
                out.errors.append(f"Load CSV failed: {res.error or 'no data'}")
            else:
                self.has_data = True
                self.loaded_samples = res.recording.samples
                self.loaded_csv_path = res.path
                out.loaded_recording = res.recording
                out.logs.append(f"Loaded {len(res.recording.samples)} samples from {res.path.name}")
        while True:
            try:
                res = self.calibration_results.get_nowait()
            except queue.Empty:
                break
            self.is_calibrating_live = False
            out.state_changed = True
            if res.error or res.calibration is None:
                out.errors.append(f"Live calibration failed: {res.error or 'unknown error'}")
            else:
                self.live_calibration = res.calibration.normalized()
                out.logs.append(
                    f"Live calibration: {self.live_calibration.mean_uv_per_count:.4g} uV/count "
                    f"(CV {self.live_calibration.cv_percent:.2f}%)"
                )
        # Detect an unexpected end of stream (e.g., device unplugged mid-record):
        # the worker thread was created and has since died, yet we still believe
        # we are streaming. (Guard on "thread existed" so simulations without a
        # real worker thread don't misfire.)
        thread = getattr(self.worker, "thread", None)
        worker_finished = thread is not None and not thread.is_alive()
        if self.is_streaming and not self.is_starting and worker_finished:
            self.is_streaming = False
            out.state_changed = True
            out.errors.append("Streaming stopped unexpectedly (device disconnected?)")
        # finalize a stopped recording once the CSV writer thread has ended
        if self._finalization_pending and not self.is_streaming and not self._worker_alive():
            self._finalize_recording(out)
            out.state_changed = True
        return out

    def drain_samples(self, limit: int = MAX_SAMPLES_PER_DRAIN) -> list[StreamSample]:
        drained: list[StreamSample] = []
        for _ in range(limit):
            try:
                drained.append(self.samples.get_nowait())
            except queue.Empty:
                break
        if drained:
            self.has_data = True
        return drained
