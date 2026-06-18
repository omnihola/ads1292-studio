from __future__ import annotations

from pathlib import Path
import queue
import threading

from ads1292_studio.csv_io import CsvRecorder
from ads1292_studio.device import Ads1x9xDevice
from ads1292_studio.models import StreamSample


class LiveWorker:
    def __init__(self, sample_queue: queue.Queue[StreamSample], log_queue: queue.Queue[str]) -> None:
        self.sample_queue = sample_queue
        self.log_queue = log_queue
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.device: Ads1x9xDevice | None = None

    def start(self, port: str, csv_path: Path | None) -> None:
        self.stop()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(port, csv_path), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.device is not None:
            try:
                self.device.close()
            except Exception as exc:
                self.log_queue.put(f"Close warning: {exc}")
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _run(self, port: str, csv_path: Path | None) -> None:
        recorder_cm = CsvRecorder(csv_path) if csv_path else None
        recorder = None
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
                device.start_stream()
                self.log_queue.put("Streaming started")
                for sample in device.iter_stream_samples():
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
