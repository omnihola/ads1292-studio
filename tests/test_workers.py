from __future__ import annotations

from pathlib import Path
import queue

from ads1292_studio.calibration import LiveStreamCalibration
from ads1292_studio.app import ConnectResult
from ads1292_studio.models import RawSample, StreamSample, StreamStartResult
from ads1292_studio.workers import AcquisitionMode, LiveWorker, reindex_raw_samples
import ads1292_studio.workers as workers


def test_connect_result_holds_success_detail() -> None:
    result = ConnectResult(port="/dev/fake", detail="firmware 1.0, ID 0x23")

    assert result.port == "/dev/fake"
    assert result.detail == "firmware 1.0, ID 0x23"
    assert result.error is None


def test_connect_result_holds_error() -> None:
    result = ConnectResult(port="/dev/fake", error="timed out")

    assert result.error == "timed out"
    assert result.detail is None


def test_live_worker_stop_only_sets_event_without_closing_device() -> None:
    worker = LiveWorker(queue.Queue(), queue.Queue(), queue.Queue())

    class FakeDevice:
        def __init__(self) -> None:
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1

    fake_device = FakeDevice()
    worker.device = fake_device

    worker.stop()

    assert worker.stop_event.is_set()
    assert fake_device.close_calls == 0


class _FakeStreamingDevice:
    def __init__(self, port: str) -> None:
        self.port = port

    def __enter__(self) -> "_FakeStreamingDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def query_firmware(self) -> str:
        return "1.0"

    def start_stream(self) -> None:
        return None

    def stop_stream(self) -> None:
        return None

    def read_stream_sample_batch(self):
        return (
            StreamSample(
                timestamp=0.0,
                ch1=0,
                ch2=0,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            ),
        )

    def iter_stream_samples(self):
        for index in range(3):
            yield StreamSample(
                timestamp=float(index),
                ch1=index,
                ch2=index,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            )


class _FakeFailingDevice:
    def __init__(self, port: str) -> None:
        self.port = port

    def __enter__(self) -> "_FakeFailingDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def query_firmware(self) -> str:
        return "1.0"

    def start_stream(self) -> None:
        raise RuntimeError("device not responding")


def test_live_worker_posts_success_result_when_stream_starts(monkeypatch) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _FakeStreamingDevice)
    sample_queue: queue.Queue = queue.Queue()
    start_queue: queue.Queue = queue.Queue()
    worker = LiveWorker(sample_queue, queue.Queue(), start_queue)

    worker.start("fake-port", None)
    result = start_queue.get(timeout=2.0)
    worker.stop()
    if worker.thread:
        worker.thread.join(timeout=2.0)

    assert result == StreamStartResult(ok=True)


def test_live_worker_posts_failure_result_when_start_stream_raises(monkeypatch) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _FakeFailingDevice)
    start_queue: queue.Queue = queue.Queue()
    worker = LiveWorker(queue.Queue(), queue.Queue(), start_queue)

    worker.start("fake-port", None)
    result = start_queue.get(timeout=2.0)
    if worker.thread:
        worker.thread.join(timeout=2.0)

    assert result.ok is False
    assert "device not responding" in (result.error or "")


class _NoFramesThenFramesDevice:
    instances: list["_NoFramesThenFramesDevice"] = []

    def __init__(self, port: str) -> None:
        self.port = port
        self.start_calls = 0
        _NoFramesThenFramesDevice.instances.append(self)

    def __enter__(self) -> "_NoFramesThenFramesDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def query_firmware(self) -> str:
        return "1.0"

    def start_stream(self) -> None:
        self.start_calls += 1

    def stop_stream(self) -> None:
        return None

    def read_stream_sample_batch(self):
        if self.start_calls < 2:
            return ()
        return (
            StreamSample(
                timestamp=0.0,
                ch1=11,
                ch2=22,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            ),
        )

    def iter_stream_samples(self, *, should_continue=None):
        return
        yield


class _NeverFramesDevice(_NoFramesThenFramesDevice):
    def read_stream_sample_batch(self):
        return ()


def test_live_worker_retries_toggle_when_start_produces_no_frames(monkeypatch) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _NoFramesThenFramesDevice)
    _NoFramesThenFramesDevice.instances.clear()
    sample_queue: queue.Queue = queue.Queue()
    start_queue: queue.Queue = queue.Queue()
    worker = LiveWorker(
        sample_queue,
        queue.Queue(),
        start_queue,
        stream_start_timeout_seconds=0.01,
    )

    worker.start("fake-port", None)
    result = start_queue.get(timeout=2.0)
    if worker.thread:
        worker.thread.join(timeout=2.0)

    assert result == StreamStartResult(ok=True)
    assert _NoFramesThenFramesDevice.instances[0].start_calls == 2
    assert sample_queue.get_nowait().ch2 == 22


def test_live_worker_reports_start_failure_when_no_stream_frames_arrive(monkeypatch) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _NeverFramesDevice)
    start_queue: queue.Queue = queue.Queue()
    worker = LiveWorker(
        queue.Queue(),
        queue.Queue(),
        start_queue,
        stream_start_timeout_seconds=0.01,
    )

    worker.start("fake-port", None)
    result = start_queue.get(timeout=2.0)
    if worker.thread:
        worker.thread.join(timeout=2.0)

    assert result.ok is False
    assert "No streaming data" in (result.error or "")


class _StreamSpyDevice:
    instances: list["_StreamSpyDevice"] = []

    def __init__(self, port: str, *args, **kwargs) -> None:
        self.port = port
        self.should_continue: object = "UNSET"
        _StreamSpyDevice.instances.append(self)

    def __enter__(self) -> "_StreamSpyDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def query_firmware(self) -> str:
        return "1.0"

    def start_stream(self) -> None:
        return None

    def stop_stream(self) -> None:
        return None

    def read_stream_sample_batch(self):
        return (
            StreamSample(
                timestamp=0.0,
                ch1=0,
                ch2=0,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            ),
        )

    def iter_stream_samples(self, *, should_continue=None):
        self.should_continue = should_continue
        yield StreamSample(
            timestamp=0.0,
            ch1=0,
            ch2=0,
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )


def test_live_worker_passes_stop_predicate_to_stream(monkeypatch) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _StreamSpyDevice)
    _StreamSpyDevice.instances.clear()
    worker = LiveWorker(queue.Queue(), queue.Queue(), queue.Queue())

    worker.start("fake-port", None)
    if worker.thread:
        worker.thread.join(timeout=2.0)

    assert _StreamSpyDevice.instances, "worker never constructed a device"
    assert callable(_StreamSpyDevice.instances[0].should_continue)


class _FakeRawDevice:
    instances: list["_FakeRawDevice"] = []

    def __init__(self, port: str, *args, **kwargs) -> None:
        self.port = port
        self.query_calls = 0
        self.stream_calls = 0
        self.raw_calls: list[int] = []
        _FakeRawDevice.instances.append(self)

    def __enter__(self) -> "_FakeRawDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def query_firmware(self) -> str:
        self.query_calls += 1
        return "1.0"

    def start_stream(self) -> None:
        self.stream_calls += 1

    def acquire_raw_samples(self, sample_count: int):
        self.raw_calls.append(sample_count)
        return (
            RawSample(timestamp=0.0, sample_index=0, ch1_raw24=111, ch2_raw24=222, status_byte=0),
            RawSample(timestamp=0.002, sample_index=1, ch1_raw24=112, ch2_raw24=223, status_byte=1),
        )


class _RawTimeoutThenSamplesDevice(_FakeRawDevice):
    def acquire_raw_samples(self, sample_count: int):
        self.raw_calls.append(sample_count)
        if len(self.raw_calls) == 1:
            raise TimeoutError("Expected 1 bytes, got 0")
        return (
            RawSample(timestamp=0.0, sample_index=0, ch1_raw24=11, ch2_raw24=22, status_byte=0),
        )


class _RawFailsAfterFirstChunkDevice(_FakeRawDevice):
    def acquire_raw_samples(self, sample_count: int):
        self.raw_calls.append(sample_count)
        if len(self.raw_calls) == 1:
            return (
                RawSample(timestamp=0.0, sample_index=0, ch1_raw24=5, ch2_raw24=6, status_byte=0),
            )
        raise RuntimeError("device disconnected mid-stream")


def test_worker_raw_mode_does_not_publish_failure_after_successful_start(
    monkeypatch, tmp_path: Path
) -> None:
    """Once raw acquisition has published ok=True, a later chunk error must not
    publish a contradicting ok=False onto the single-shot start-result queue."""
    monkeypatch.setattr(workers, "Ads1x9xDevice", _RawFailsAfterFirstChunkDevice)
    _RawFailsAfterFirstChunkDevice.instances.clear()
    start_queue: queue.Queue = queue.Queue()
    worker = LiveWorker(queue.Queue(), queue.Queue(), start_queue, raw_chunk_samples=8)

    worker.start("fake-port", tmp_path / "raw.csv", mode=AcquisitionMode.RAW)
    first = start_queue.get(timeout=2.0)
    if worker.thread:
        worker.thread.join(timeout=2.0)  # let the 2nd chunk crash the worker

    remaining = []
    while True:
        try:
            remaining.append(start_queue.get_nowait())
        except queue.Empty:
            break

    assert first == StreamStartResult(ok=True)
    assert remaining == []  # no contradicting ok=False after a successful start


def test_worker_raw_mode_acquires_raw_samples_without_starting_live_stream(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _FakeRawDevice)
    _FakeRawDevice.instances.clear()
    sample_queue: queue.Queue = queue.Queue()
    start_queue: queue.Queue = queue.Queue()
    csv_path = tmp_path / "raw.csv"
    worker = LiveWorker(sample_queue, queue.Queue(), start_queue, raw_chunk_samples=8)

    worker.start("fake-port", csv_path, mode=AcquisitionMode.RAW)
    result = start_queue.get(timeout=2.0)
    worker.stop()
    if worker.thread:
        worker.thread.join(timeout=2.0)

    assert result == StreamStartResult(ok=True)
    assert _FakeRawDevice.instances[0].stream_calls == 0
    assert _FakeRawDevice.instances[0].raw_calls
    assert set(_FakeRawDevice.instances[0].raw_calls) == {8}
    assert sample_queue.get_nowait().ch1 == 111
    assert "ch1_raw24,ch2_raw24" in csv_path.read_text()


def test_worker_raw_mode_retries_transient_raw_timeout(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(workers, "Ads1x9xDevice", _RawTimeoutThenSamplesDevice)
    _RawTimeoutThenSamplesDevice.instances.clear()
    sample_queue: queue.Queue = queue.Queue()
    log_queue: queue.Queue = queue.Queue()
    start_queue: queue.Queue = queue.Queue()
    worker = LiveWorker(sample_queue, log_queue, start_queue, raw_chunk_samples=8)

    worker.start("fake-port", tmp_path / "raw.csv", mode=AcquisitionMode.RAW)
    result = start_queue.get(timeout=2.0)
    worker.stop()
    if worker.thread:
        worker.thread.join(timeout=2.0)
    logs = [log_queue.get_nowait() for _ in range(log_queue.qsize())]

    assert result == StreamStartResult(ok=True)
    assert _RawTimeoutThenSamplesDevice.instances[0].raw_calls == [8, 8]
    assert sample_queue.get_nowait().ch2 == 22
    assert any("Raw acquisition timeout; retrying" in log for log in logs)


def test_worker_live_mode_writes_live_calibration_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "live.csv"
    calibration = LiveStreamCalibration(
        mean_uv_per_count=1.895,
        std_uv_per_count=0.001,
        cv_percent=0.05,
        runs=5,
        test_signal_pp_uv=2016.6666666667,
    )
    worker = LiveWorker(queue.Queue(), queue.Queue(), queue.Queue())

    recorder = worker._recorder(csv_path, AcquisitionMode.LIVE, None, calibration)
    assert recorder is not None
    with recorder:
        recorder.write(
            StreamSample(
                timestamp=0.0,
                ch1=0,
                ch2=123,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            )
        )

    text = csv_path.read_text()
    assert "live_scale_uv_per_count" in text
    assert "live_processed" in text


def test_reindex_raw_samples_keeps_chunked_raw_recording_monotonic() -> None:
    samples = (
        RawSample(timestamp=10.0, sample_index=0, ch1_raw24=1, ch2_raw24=2, status_byte=0),
        RawSample(timestamp=10.002, sample_index=1, ch1_raw24=3, ch2_raw24=4, status_byte=0),
    )

    reindexed = reindex_raw_samples(samples, start_index=8, sample_rate_hz=500.0)

    assert [sample.sample_index for sample in reindexed] == [8, 9]
    assert [sample.timestamp for sample in reindexed] == [0.016, 0.018]
    assert [sample.ch2_raw24 for sample in reindexed] == [2, 4]
