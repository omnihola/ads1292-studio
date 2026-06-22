"""Entry point for the PySide6 front-end (``ads1292-studio-qt``)."""
from __future__ import annotations

import sys

from ads1292_studio.matplotlib_runtime import configure_matplotlib_cache

configure_matplotlib_cache()

from ads1292_studio.macos_stderr import install_macos_stderr_filter  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from ads1292_studio.ui_qt.main_window import MainWindow  # noqa: E402
from ads1292_studio.ui_qt.theme import apply_theme  # noqa: E402


def main() -> None:
    # Install early (before the Qt app) so macOS Input Method (IMK) console
    # noise, e.g. "IMKCFRunLoopWakeUpReliable", is filtered from stderr.
    install_macos_stderr_filter()
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, mode="light")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
