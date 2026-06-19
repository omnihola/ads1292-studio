from ads1292_studio.macos_stderr import should_suppress_stderr_line


def test_suppresses_macos_imk_wakeup_noise() -> None:
    line = "2026-06-19 02:37:17.008 python[87244:2955267] error messaging the mach port for IMKCFRunLoopWakeUpReliable\n"

    assert should_suppress_stderr_line(line) is True


def test_keeps_unrelated_stderr_lines_visible() -> None:
    line = "Traceback (most recent call last): RuntimeError: device disconnected\n"

    assert should_suppress_stderr_line(line) is False
