"""Pure formatting for the live recording-status indicator.

Shows elapsed time, samples captured, and the *effective* sample rate. The
effective rate (samples / wall-elapsed) makes any acquisition gap visible in
real time — research-grade transparency for capture precision.
"""
from __future__ import annotations


def format_recording_status(sample_count: int, elapsed_seconds: float, *, recording: bool) -> str:
    if not recording:
        return ""
    elapsed = max(0.0, float(elapsed_seconds))
    minutes = int(elapsed) // 60
    seconds = int(elapsed) % 60
    parts = [f"● REC {minutes:02d}:{seconds:02d}", f"{int(sample_count):,} samples"]
    if elapsed >= 1.0:
        parts.append(f"{round(sample_count / elapsed):,} Hz")
    return " · ".join(parts)
