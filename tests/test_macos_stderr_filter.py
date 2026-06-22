from ads1292_studio.macos_stderr import should_suppress_stderr_line


def test_suppresses_macos_imk_wakeup_noise() -> None:
    line = "2026-06-19 02:37:17.008 python[87244:2955267] error messaging the mach port for IMKCFRunLoopWakeUpReliable\n"

    assert should_suppress_stderr_line(line) is True


def test_keeps_unrelated_stderr_lines_visible() -> None:
    line = "Traceback (most recent call last): RuntimeError: device disconnected\n"

    assert should_suppress_stderr_line(line) is False


def test_suppresses_known_macos_tk_input_service_noise() -> None:
    noisy_lines = (
        "2026-06-19 03:31:23.797 python[24389:3055412] TISFileInterrogator updateSystemInputSources false but old data invalid\n",
        "2026-06-19 03:31:23.803 python[24389:3055568] Connection Invalid error for service com.apple.hiservices-xpcservice.\n",
        "2026-06-19 03:31:23.803 python[24389:3055412] Error received in message reply handler: Connection invalid\n",
        "Keyboard Layouts: duplicate keyboard layout identifier -17410.\n",
        "Keyboard Layouts: keyboard layout identifier -17410 has been replaced with -28673.\n",
        "2026-06-19 03:31:23.868 python[24389:3055412] Failure on line 688 in function id scheduleApplicationNotification(LSNotificationCode, NSWorkspaceNotificationCenter *): noErr == _LSModifyNotification(notificationID, 1, &code, 0, NULL, NULL, NULL)\n",
    )

    assert all(should_suppress_stderr_line(line) for line in noisy_lines)


def test_app_installs_macos_stderr_filter_before_tk_initialization() -> None:
    import inspect

    from ads1292_studio.app import App

    source = inspect.getsource(App.__init__)

    assert "install_macos_stderr_filter()" in source
    assert source.index("install_macos_stderr_filter()") < source.index("super().__init__()")


def test_qt_app_installs_macos_stderr_filter_before_qapplication() -> None:
    import inspect

    from ads1292_studio import app_qt

    source = inspect.getsource(app_qt.main)

    assert "install_macos_stderr_filter()" in source
    assert source.index("install_macos_stderr_filter()") < source.index("QApplication")
