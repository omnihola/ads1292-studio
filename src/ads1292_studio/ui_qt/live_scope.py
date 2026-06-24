"""Real-time ECG/respiration scope backed by pyqtgraph.

pyqtgraph is purpose-built for live plotting (~10-100x faster than a full
matplotlib redraw), so the streaming view stays smooth at wide windows and
during RAW bursts. The review/analysis tabs remain matplotlib. This class keeps
the same public API the controller drives on the live panel:
update_traces / set_autoscale / set_calibration / set_sweep_speed /
set_event_markers, plus the _uv_per_count / _autoscale_enabled attributes.
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ads1292_studio.ui_qt.tokens import design_tokens

_T = design_tokens()


class LiveScope(QWidget):
    def __init__(self) -> None:
        super().__init__()
        pg.setConfigOptions(antialias=True)
        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground(_T["panel"])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._glw)

        self.p_ecg = self._glw.addPlot(row=0, col=0)
        self.p_resp = self._glw.addPlot(row=1, col=0)
        self.p_resp.setXLink(self.p_ecg)
        for plot in (self.p_ecg, self.p_resp):
            plot.showGrid(x=True, y=True, alpha=0.25)
            for side in ("left", "bottom"):
                axis = plot.getAxis(side)
                axis.setPen(_T["border_strong"])
                axis.setTextPen(_T["ink_faint"])
        self._ecg_curve = self.p_ecg.plot(pen=pg.mkPen(_T["ecg"], width=1.2))
        self._resp_curve = self.p_resp.plot(pen=pg.mkPen(_T["resp"], width=1.2))
        # The caller pre-decimates to <=4000 peak-preserving points, so pyqtgraph
        # renders fast without its own clip/downsample (which require a realized
        # ViewBox and crash in headless/early construction).
        self.p_resp.setLabel("bottom", "Time (s)")

        self._uv_per_count: float | None = None
        self._autoscale_enabled = True
        self._event_items: list = []
        # Drive ranges explicitly (NOT pyqtgraph autoRange): autoRange is
        # poisoned by the vertical event-marker InfiniteLines (infinite Y extent
        # -> range explodes to ~1e12) and doesn't reliably track the data.
        for plot in (self.p_ecg, self.p_resp):
            plot.disableAutoRange()
            plot.setYRange(-1.0, 1.0, padding=0)
            plot.setXRange(0.0, 8.0, padding=0)
        self.set_calibration(None)  # sets titles + y labels

    # ---- public API (mirrors the matplotlib LivePanel) ----
    def update_traces(self, ecg_x, ecg_y, resp_x, resp_y) -> None:
        scale = self._uv_per_count
        ex = np.asarray(ecg_x, dtype=float)
        rx = np.asarray(resp_x, dtype=float)
        ey = np.asarray(ecg_y, dtype=float)
        ry = np.asarray(resp_y, dtype=float)
        if scale is not None:
            ey = ey * scale
            ry = ry * scale
        self._ecg_curve.setData(ex, ey)
        self._resp_curve.setData(rx, ry)
        # X always follows the visible window
        if ex.size:
            right = float(ex[-1]) if ex[-1] > ex[0] else float(ex[0]) + 1.0
            self.p_ecg.setXRange(float(ex[0]), right, padding=0)
        # Y is computed explicitly from the data (only when autoscale is on),
        # so event-marker InfiniteLines never poison the range.
        if self._autoscale_enabled:
            self._autoscale_y(self.p_ecg, ey)
            self._autoscale_y(self.p_resp, ry)

    @staticmethod
    def _autoscale_y(plot, ys: np.ndarray) -> None:
        if ys.size == 0:
            return
        lo = float(np.min(ys))
        hi = float(np.max(ys))
        if not (np.isfinite(lo) and np.isfinite(hi)):
            return
        if hi <= lo:
            hi, lo = lo + 1.0, lo - 1.0
        pad = (hi - lo) * 0.12
        plot.setYRange(lo - pad, hi + pad, padding=0)

    def set_autoscale(self, enabled: bool) -> None:
        self._autoscale_enabled = bool(enabled)
        for plot in (self.p_ecg, self.p_resp):
            plot.disableAutoRange(axis="y")

    def set_calibration(self, uv_per_count: float | None) -> None:
        self._uv_per_count = uv_per_count
        if uv_per_count is not None:
            self.p_ecg.setLabel("left", "Amplitude (µV)")
            self.p_resp.setLabel("left", "Impedance (µV)")
            self.p_ecg.setTitle(f"CH2 ECG Lead I  [cal {uv_per_count:.4g} µV/ct]", color=_T["ink"])
        else:
            self.p_ecg.setLabel("left", "Amplitude (counts)")
            self.p_resp.setLabel("left", "Impedance (counts)")
            self.p_ecg.setTitle("CH2 ECG Lead I", color=_T["ink"])
        self.p_resp.setTitle("CH1 Respiration raw", color=_T["ink"])

    def set_sweep_speed(self, mm_s: int) -> None:
        minor = 0.2 if int(mm_s) == 25 else 0.1
        self.p_ecg.getAxis("bottom").setTickSpacing(major=1.0, minor=minor)

    def set_event_markers(self, markers, pending_range_start: float | None = None) -> None:
        for item in self._event_items:
            self.p_ecg.removeItem(item)
        self._event_items = []
        for marker in markers:
            duration = getattr(marker, "duration_seconds", 0.0)
            if duration > 0:
                region = pg.LinearRegionItem(
                    values=(marker.timestamp_seconds, marker.timestamp_seconds + duration),
                    movable=False, brush=pg.mkBrush(200, 136, 30, 40),
                )
                self.p_ecg.addItem(region)
                self._event_items.append(region)
            else:
                line = pg.InfiniteLine(
                    pos=marker.timestamp_seconds, angle=90,
                    pen=pg.mkPen(_T["warn"], width=1.0, style=Qt.PenStyle.DotLine),
                )
                self.p_ecg.addItem(line)
                self._event_items.append(line)
        if pending_range_start is not None:
            pending = pg.InfiniteLine(
                pos=pending_range_start, angle=90,
                pen=pg.mkPen(_T["indigo"], width=1.4, style=Qt.PenStyle.DashLine),
            )
            self.p_ecg.addItem(pending)
            self._event_items.append(pending)

    # ---- introspection (tests / diagnostics) ----
    def ecg_y(self) -> list[float]:
        data = self._ecg_curve.getData()
        return list(data[1]) if data[1] is not None else []

    def ecg_x(self) -> list[float]:
        data = self._ecg_curve.getData()
        return list(data[0]) if data[0] is not None else []
