"""Pure formatting for the live recording-status HUD (elapsed · samples · Hz)."""
from __future__ import annotations

from ads1292_studio.recording_status import format_recording_status


def test_idle_when_not_recording() -> None:
    assert format_recording_status(0, 0.0, recording=False) == ""


def test_elapsed_is_mm_ss() -> None:
    text = format_recording_status(76540, 154.0, recording=True)
    assert text.startswith("● REC 02:34")
    assert "76,540 samples" in text


def test_effective_rate_shown_and_rounded() -> None:
    # 5000 samples over 10 s -> 500 Hz
    text = format_recording_status(5000, 10.0, recording=True)
    assert "500 Hz" in text


def test_zero_elapsed_does_not_divide_by_zero() -> None:
    text = format_recording_status(10, 0.0, recording=True)
    assert "REC 00:00" in text
    assert "Hz" not in text  # no rate until time elapses


def test_long_session_hours_in_mm_ss_overflow() -> None:
    # 1 hour 1 min 5 s -> 61:05 (mm:ss keeps counting minutes)
    text = format_recording_status(100, 3665.0, recording=True)
    assert "61:05" in text
