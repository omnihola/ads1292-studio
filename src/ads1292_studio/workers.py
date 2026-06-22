from __future__ import annotations

from enum import Enum
from dataclasses import replace
from pathlib import Path
import queue
import threading
import time

from ads1292_studio.calibration import Calibration, LiveStreamCalibration
from ads1292_studio.csv_io import CsvRecorder, RawCsvRecorder
from ads1292_studio.device import Ads1x9xDevice
from ads1292_studio.models import StreamSample, StreamStartResult
from ads1292_studio.models import RawSample


class AcquisitionMode(str, Enum):
    LIVE = "live"
    RAW = "raw"


def reindex_raw_samples(
    samples: tuple[RawSample, ...],
    *,
    start_index: int,
    sample_rate_hz: float,
) -> tuple[RawSample, ...]:
    return tuple(
        replace(
            sample,
            sample_index=start_index + offset,
            timestamp=round((start_index + offset) / sample_rate_hz, 6),
        )
        for offset, sample in enumerate(samples)
    )


class LiveWorker:
    def __init__(
        self,
        sample_queue: queue.Queue[StreamSample],
        log_queue: queue.Queue[str],
        start_result_queue: queue.Queue[StreamStartResult],
        *,
        stream_start_timeout_seconds: float = 1.0,
        raw_chunk_samples: int = 500,
    ) -> None:
        self.sample_queue = sample_queue
        self.log_queue = log_queue
        self.start_result_queue = start_result_queue
        self.stream_start_timeout_seconds = max(0.01, float(stream_start_timeout_seconds))
        self.raw_chunk_samples = max(8, int(raw_chunk_samples) - (int(raw_chunk_samples) % 8))
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.device: Ads1x9xDevice | None = None
        self.raw_sample_index = 0
        # wall-clock (monotonic) of the first/last sample actually produced,
        # for measuring the true effective acquisition rate
        self.acq_first_monotonic: float | None = None
        self.acq_last_monotonic: float | None = None

    def _note_sample_wall(self) -> None:
        now = time.monotonic()
        if self.acq_first_monotonic is None:
            self.acq_first_monotonic = now
        self.acq_last_monotonic = now

    def start(
        self,
        port: str,
        csv_path: Path | None,
        *,
        mode: AcquisitionMode | str = AcquisitionMode.LIVE,
        calibration: Calibration | None = None,
        live_calibration: LiveStreamCalibration | None = None,
    ) -> None:
        self._stop_and_wait()
        self.stop_event.clear()
        self.raw_sample_index = 0
        self.acq_first_monotonic = None
        self.acq_last_monotonic = None
        acquisition_mode = AcquisitionMode(mode)
        self.thread = threading.Thread(
            target=self._run,
            args=(port, csv_path, acquisition_mode, calibration, live_calibration),
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _stop_and_wait(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _run(
        self,
        port: str,
        csv_path: Path | None,
        mode: AcquisitionMode,
        calibration: Calibration | None,
        live_calibration: LiveStreamCalibration | None,
    ) -> None:
        recorder_cm = self._recorder(csv_path, mode, calibration, live_calibration) if csv_path else None
        recorder = None
        started = False
        try:
            if recorder_cm:
                recorder = recorder_cm.__enter__()
                self.log_queue.put(f"Saving CSV: {csv_path}")
            with Ads1x9xDevice(port) as device:
                self.device = device
                try:
                    self.log_queue.put(f"Firmware: {device.query_firmware()}")
                except Exception as exc:
                    self.log_queue.put(f"Firmware query failed: {exc}")
                if mode is AcquisitionMode.RAW:
                    self._run_raw(device, recorder)
                    started = True
                    return
                initial_samples = self._start_stream_and_wait_for_data(device)
                started = True
                self.start_result_queue.put(StreamStartResult(ok=True))
                self.log_queue.put("Streaming started")
                for sample in initial_samples:
                    self._note_sample_wall()
                    self.sample_queue.put(sample)
                    if recorder is not None:
                        recorder.write(sample)
                for sample in device.iter_stream_samples(
                    should_continue=lambda: not self.stop_event.is_set()
                ):
                    if self.stop_event.is_set():
                        break
                    self._note_sample_wall()
                    self.sample_queue.put(sample)
                    if recorder is not None:
                        recorder.write(sample)
                try:
                    device.stop_stream()
                except Exception as exc:
                    self.log_queue.put(f"Stop stream warning: {exc}")
        except Exception as exc:
            if not started:
                self.start_result_queue.put(StreamStartResult(ok=False, error=str(exc)))
            self.log_queue.put(f"ERROR: {exc}")
        finally:
            if recorder_cm:
                try:
                    recorder_cm.__exit__(None, None, None)
                    rows = recorder_cm.rows_written
                    self.log_queue.put(f"CSV closed: {csv_path} ({rows} samples)")
                except Exception as exc:
                    self.log_queue.put(f"CSV close error: {exc}")
            self.device = None
            self.log_queue.put("Stopped")

    def _recorder(
        self,
        csv_path: Path | None,
        mode: AcquisitionMode,
        calibration: Calibration | None,
        live_calibration: LiveStreamCalibration | None = None,
    ):
        if csv_path is None:
            return None
        if mode is AcquisitionMode.RAW:
            return RawCsvRecorder(csv_path, calibration=calibration or Calibration())
        return CsvRecorder(csv_path, live_calibration=live_calibration)

    def _run_raw(self, device: Ads1x9xDevice, recorder: RawCsvRecorder | None) -> None:
        self.log_queue.put(f"Raw acquisition mode: {self.raw_chunk_samples} samples per chunk")
        first_chunk = self._acquire_raw_chunk_with_retry(device)
        sample_rate_hz = float(getattr(device, "sample_rate_hz", 500.0))
        self.start_result_queue.put(StreamStartResult(ok=True))
        self.log_queue.put("Raw acquisition started")
        self._emit_raw_samples(first_chunk, recorder, sample_rate_hz=sample_rate_hz)
        while not self.stop_event.is_set():
            chunk = self._acquire_raw_chunk_with_retry(device)
            self._emit_raw_samples(chunk, recorder, sample_rate_hz=sample_rate_hz)

    def _acquire_raw_chunk_with_retry(self, device: Ads1x9xDevice) -> tuple[RawSample, ...]:
        while not self.stop_event.is_set():
            try:
                return device.acquire_raw_samples(self.raw_chunk_samples)
            except TimeoutError as exc:
                self.log_queue.put(f"Raw acquisition timeout; retrying: {exc}")
                time.sleep(0.05)
        return tuple()

    def _emit_raw_samples(
        self,
        samples: tuple[RawSample, ...],
        recorder: RawCsvRecorder | None,
        *,
        sample_rate_hz: float,
    ) -> None:
        reindexed = reindex_raw_samples(
            tuple(samples),
            start_index=self.raw_sample_index,
            sample_rate_hz=sample_rate_hz,
        )
        self.raw_sample_index += len(reindexed)
        for sample in reindexed:
            self._note_sample_wall()
            self.sample_queue.put(sample.as_stream_sample())
            if recorder is not None:
                recorder.write(sample)

    def _start_stream_and_wait_for_data(self, device: Ads1x9xDevice) -> tuple[StreamSample, ...]:
        for attempt in range(2):
            if self.stop_event.is_set():
                raise TimeoutError("Start cancelled before streaming data arrived")
            device.start_stream()
            batch = self._wait_for_stream_batch(device)
            if batch:
                if attempt:
                    self.log_queue.put("Streaming recovered after retrying start toggle")
                return batch
            if attempt == 0:
                self.log_queue.put("No streaming data after start command; retrying toggle")
            else:
                self.log_queue.put("No streaming data after retry")
        raise TimeoutError("No streaming data received after Start")

    def _wait_for_stream_batch(self, device: Ads1x9xDevice) -> tuple[StreamSample, ...]:
        deadline = time.monotonic() + self.stream_start_timeout_seconds
        while time.monotonic() < deadline and not self.stop_event.is_set():
            batch = device.read_stream_sample_batch()
            if batch:
                return tuple(batch)
        return tuple()
