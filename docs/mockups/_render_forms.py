"""Render the Validation (and Protocol) left-tab forms for verification."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from ads1292_studio.ui_qt.main_window import MainWindow
from ads1292_studio.ui_qt.theme import apply_theme

app = QApplication.instance() or QApplication([])
apply_theme(app)
win = MainWindow()
win.resize(1400, 880)
win.show()
app.processEvents()
win.sidebar.setCurrentIndex(1)  # Validation
app.processEvents()
win.grab().save("docs/mockups/2026-06-21-pyqt-validation.png")
win.sidebar.setCurrentIndex(2)  # Protocol
app.processEvents()
win.grab().save("docs/mockups/2026-06-21-pyqt-protocol.png")
print("OK", "gate:", win.sidebar.quality_gate().min_contact_ok_percent, "steps:", len(win.sidebar.protocol().steps))
