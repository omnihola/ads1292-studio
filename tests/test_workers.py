from __future__ import annotations

import queue

from ads1292_studio.app import ConnectResult
from ads1292_studio.models import StreamSample, StreamStartResult
from ads1292_studio.workers import LiveWorker
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
