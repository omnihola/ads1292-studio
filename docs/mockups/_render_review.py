"""Load a real recording and render the Review/PQRST/Spectrum tabs (verification)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.ui_qt.main_window import MainWindow
from ads1292_studio.ui_qt.theme import apply_theme

app = QApplication.instance() or QApplication([])
apply_theme(app)
win = MainWindow()
win.resize(1400, 880)
win.show()
app.processEvents()

rec = read_recording_csv("recordings/2026-06-18-221342-ads1292-studio.csv")
win._show_recording(rec)  # review + quality + pqrst + spectrum
app.processEvents()

win.tabs.setCurrentWidget(win.tabs.widget(3))  # Spectrum
app.processEvents()
win.spectrum_panel.draw()
win.grab().save("docs/mockups/2026-06-21-pyqt-spectrum.png")

win.tabs.setCurrentWidget(win.tabs.widget(2))  # PQRST
app.processEvents()
win.pqrst_panel.draw()
win.grab().save("docs/mockups/2026-06-21-pyqt-pqrst.png")

print("OK rendered; samples:", len(rec.samples))
