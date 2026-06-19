from __future__ import annotations

import queue

from ads1292_studio.app import ConnectResult


def test_connect_result_holds_success_detail() -> None:
    result = ConnectResult(port="/dev/fake", detail="firmware 1.0, ID 0x23")

    assert result.port == "/dev/fake"
    assert result.detail == "firmware 1.0, ID 0x23"
    assert result.error is None


def test_connect_result_holds_error() -> None:
    result = ConnectResult(port="/dev/fake", error="timed out")

    assert result.error == "timed out"
    assert result.detail is None
