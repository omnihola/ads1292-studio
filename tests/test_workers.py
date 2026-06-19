from __future__ import annotations

import queue

from ads1292_studio.app import ConnectResult
from ads1292_studio.workers import LiveWorker


def test_live_worker_stop_only_sets_event_without_closing_device() -> None:
    worker = LiveWorker(queue.Queue(), queue.Queue())

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


def test_connect_result_holds_success_detail() -> None:
    result = ConnectResult(port="/dev/fake", detail="firmware 1.0, ID 0x23")

    assert result.port == "/dev/fake"
    assert result.detail == "firmware 1.0, ID 0x23"
    assert result.error is None


def test_connect_result_holds_error() -> None:
    result = ConnectResult(port="/dev/fake", error="timed out")

    assert result.error == "timed out"
    assert result.detail is None
