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

import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ads1292_studio.acquisition import (
    build_acquisition_provenance,
    finalize_acquisition_provenance,
)
from ads1292_studio.calibration import Calibration
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.device import Ads1x9xDevice
from ads1292_studio.gui_state import GuiState
from ads1292_studio.gui_workers import ConnectResult, CsvLoadResult
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.models import Recording, StreamSample, StreamStartResult
from ads1292_studio.processing import build_processing_settings
from ads1292_studio.protocol import protocol_template
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.recording_bundle import recording_bundle_path, write_recording_bundle
from ads1292_studio.recording_paths import recording_csv_path
from ads1292_studio.workers import AcquisitionMode, LiveWorker
from ads1292_studio.xlsx_io import write_recording_xlsx

MAX_SAMPLES_PER_DRAIN = 1000
SAMPLE_RATE_HZ = 500.0


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
        self.worker = LiveWorker(self.samples, self.logs, self.stream_start_results)

        self.connected_port: str | None = None
        self.selected_port: str = ""
        self.recording_path: Path | None = None
        self.is_connecting = False
        self.is_starting = False
        self.is_streaming = False
        self.is_loading_csv = False
        self.has_data = False

        self._finalization_pending = False
        self._record_metadata = SessionMetadata()
        self._record_provenance = None
        self._record_started_iso = ""

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

    # ---- start / stop ----
    def start(
        self,
        port: str,
        *,
        save_csv: bool,
        mode: AcquisitionMode = AcquisitionMode.LIVE,
        metadata: SessionMetadata | None = None,
    ) -> None:
        if self.connected_port != port or self.is_streaming:
            return
        self.recording_path = None
        self._finalization_pending = False
        csv_path = None
        if save_csv:
            started_at = datetime.now()
            self._record_started_iso = started_at.isoformat(timespec="seconds")
            csv_path = recording_csv_path(started_at=started_at, acquisition_mode=mode)
            self.recording_path = csv_path
            self._record_metadata = metadata or SessionMetadata()
            self._record_provenance = build_acquisition_provenance(
                csv_path=csv_path,
                acquisition_mode=mode.value,
                port=port,
                sample_rate_hz=SAMPLE_RATE_HZ,
                calibration=Calibration(),
                live_calibration=None,
                started_at=self._record_started_iso,
            )
            self._finalization_pending = True
        self.is_starting = True
        self.worker.start(port, csv_path, mode=mode, calibration=Calibration())

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
            write_recording_bundle(
                self.recording_path,
                metadata=self._record_metadata,
                events=(),
                calibration=Calibration(),
                acquisition=provenance,
                protocol=protocol_template(),
                quality_gate=QualityGate(),
                processing=build_processing_settings(sample_rate_hz=SAMPLE_RATE_HZ),
                sample_rate_hz=SAMPLE_RATE_HZ,
                created_at=finalized,
            )
            xlsx_path = write_recording_xlsx(self.recording_path, events=(), sample_rate_hz=SAMPLE_RATE_HZ)
            out.logs.append(f"Recording finalized: {sample_count} samples")
            out.logs.append(f"Recording JSON written: {recording_bundle_path(self.recording_path)}")
            out.logs.append(f"Recording XLSX written: {xlsx_path}")
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
                out.loaded_recording = res.recording
                out.logs.append(f"Loaded {len(res.recording.samples)} samples from {res.path.name}")
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
