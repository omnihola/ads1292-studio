"""Offscreen render of the real PySide6 app to a PNG (for visual verification)."""
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ads1292_studio.models import StreamSample
from ads1292_studio.ui_qt.main_window import MainWindow
from ads1292_studio.ui_qt.theme import apply_theme

app = QApplication.instance() or QApplication([])
apply_theme(app, mode="light")
win = MainWindow()
win.resize(1400, 880)
win.show()
app.processEvents()

# simulate a connected + streaming session with a synthetic ECG-ish trace
win.controller.selected_port = "/dev/cu.usbmodem214301"
win.controller.connected_port = "/dev/cu.usbmodem214301"
win.controller.is_streaming = True
win.controller.has_data = True
fs = 500.0
for i in range(2000):
    t = i / fs
    # crude ECG: baseline + periodic spike
    phase = (i % 400)
    spike = 1800 if phase == 0 else (-600 if phase in (3, 5) else 0)
    ecg = 200 + spike + 20 * math.sin(2 * math.pi * 0.3 * t)
    resp = 500 + 300 * math.sin(2 * math.pi * 0.25 * t)
    win.controller.samples.put(
        StreamSample(timestamp=t, ch1=int(resp), ch2=int(ecg), board_heart_rate=72, board_respiration_rate=15, status_byte=0, sample_index=i)
    )
win._events.append({"label": "motion", "t": 4.0, "kind": "point"})
win._tick()
win._refresh_events()
win._refresh_state()
win.event_console.set_snr("ECG 24.6 dB · noise 3.1 µV rms · baseline stable")
win.live_panel.draw()
app.processEvents()

out = "docs/mockups/2026-06-21-pyqt-app-actual.png"
win.grab().save(out)
print("saved", out)
