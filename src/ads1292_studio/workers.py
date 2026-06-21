from __future__ import annotations

from pathlib import Path
import queue
import threading
import time

from ads1292_studio.csv_io import CsvRecorder
from ads1292_studio.device import Ads1x9xDevice
from ads1292_studio.models import StreamSample, StreamStartResult


class LiveWorker:
    def __init__(
        self,
        sample_queue: queue.Queue[StreamSample],
        log_queue: queue.Queue[str],
        start_result_queue: queue.Queue[StreamStartResult],
        *,
        stream_start_timeout_seconds: float = 1.0,
    ) -> None:
        self.sample_queue = sample_queue
        self.log_queue = log_queue
        self.start_result_queue = start_result_queue
        self.stream_start_timeout_seconds = max(0.01, float(stream_start_timeout_seconds))
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.device: Ads1x9xDevice | None = None

    def start(self, port: str, csv_path: Path | None) -> None:
        self._stop_and_wait()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(port, csv_path), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _stop_and_wait(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _run(self, port: str, csv_path: Path | None) -> None:
        recorder_cm = CsvRecorder(csv_path) if csv_path else None
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
                initial_samples = self._start_stream_and_wait_for_data(device)
                started = True
                self.start_result_queue.put(StreamStartResult(ok=True))
                self.log_queue.put("Streaming started")
                for sample in initial_samples:
                    self.sample_queue.put(sample)
                    if recorder is not None:
                        recorder.write(sample)
                for sample in device.iter_stream_samples(
                    should_continue=lambda: not self.stop_event.is_set()
                ):
                    if self.stop_event.is_set():
                        break
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
