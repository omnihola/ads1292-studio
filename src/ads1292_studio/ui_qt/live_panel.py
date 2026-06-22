"""Live ECG/respiration plot (matplotlib embedded via FigureCanvasQTAgg)."""
from __future__ import annotations

from typing import Sequence

import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from ads1292_studio.ui_qt.tokens import design_tokens

_T = design_tokens()


class LivePanel(FigureCanvasQTAgg):
    """Two synchronized panels: CH2 ECG (top) and CH1 respiration (bottom)."""

    def __init__(self) -> None:
        fig = Figure(figsize=(7.4, 3.0), facecolor=_T["panel"])
        super().__init__(fig)
        self.ax_ecg = fig.add_subplot(211)
        self.ax_resp = fig.add_subplot(212, sharex=self.ax_ecg)
        fig.subplots_adjust(left=0.07, right=0.99, top=0.93, bottom=0.12, hspace=0.45)
        self._style_axes()
        (self._ecg_line,) = self.ax_ecg.plot([], [], color=_T["ecg"], linewidth=1.1)
        (self._resp_line,) = self.ax_resp.plot([], [], color=_T["resp"], linewidth=1.1)
        self.ax_ecg.set_title("CH2 ECG Lead I", loc="left", fontsize=9, color=_T["ink"])
        self.ax_resp.set_title("CH1 Respiration raw", loc="left", fontsize=9, color=_T["ink"])
        self.ax_ecg.set_ylabel("Amplitude (counts)", fontsize=8)
        self.ax_resp.set_ylabel("Impedance (counts)", fontsize=8)
        self.ax_resp.set_xlabel("Time (s)", fontsize=8)
        self._empty_text = None
        self._event_artists: list = []
        self.show_empty("Connect, then Start for CH2 ECG")

    def _style_axes(self) -> None:
        for ax in (self.ax_ecg, self.ax_resp):
            ax.set_facecolor(_T["panel_alt"])
            ax.grid(True, color=_T["border"], linewidth=0.6, alpha=0.8)
            for spine in ax.spines.values():
                spine.set_color(_T["border"])
            ax.tick_params(colors=_T["ink_faint"], labelsize=7)

    def show_empty(self, message: str) -> None:
        """Render an empty-state placeholder message on the ECG axis."""
        self._ecg_line.set_data([], [])
        self._resp_line.set_data([], [])
        if self._empty_text is not None:
            self._empty_text.remove()
        self._empty_text = self.ax_ecg.text(
            0.5, 0.5, message, transform=self.ax_ecg.transAxes,
            ha="center", va="center", color=_T["ink_faint"], fontsize=11, fontweight="bold",
        )
        self.draw_idle()

    def update_traces(
        self,
        ecg_x: Sequence[float],
        ecg_y: Sequence[float],
        resp_x: Sequence[float],
        resp_y: Sequence[float],
    ) -> None:
        """Replace the trace data and autoscale to the visible window."""
        if self._empty_text is not None:
            self._empty_text.remove()
            self._empty_text = None
        self._ecg_line.set_data(ecg_x, ecg_y)
        self._resp_line.set_data(resp_x, resp_y)
        self._autoscale(self.ax_ecg, ecg_x, ecg_y)
        self._autoscale(self.ax_resp, resp_x, resp_y)
        self.draw_idle()

    def render_recording(self, samples, sample_rate_hz: float, ecg_source: str | None = None) -> None:
        """Uniform renderer interface (RecordingRenderer): plot a full recording, decimated."""
        if not samples:
            self.show_empty("No samples in recording")
            return
        step = max(1, len(samples) // 4000)
        xs = [s.timestamp for s in samples[::step]]
        ecg = [float(s.ch2) for s in samples[::step]]
        resp = [float(s.ch1) for s in samples[::step]]
        self.update_traces(xs, ecg, xs, resp)

    def set_event_markers(self, markers) -> None:
        """Overlay point events (dotted line) and range events (shaded span) on the ECG axis."""
        for art in self._event_artists:
            try:
                art.remove()
            except (ValueError, AttributeError):
                pass
        self._event_artists = []
        for m in markers:
            if getattr(m, "duration_seconds", 0.0) > 0:
                span = self.ax_ecg.axvspan(
                    m.timestamp_seconds, m.timestamp_seconds + m.duration_seconds,
                    color=_T["warn"], alpha=0.16,
                )
                self._event_artists.append(span)
            else:
                line = self.ax_ecg.axvline(m.timestamp_seconds, color=_T["warn"], linewidth=1.0, linestyle=":")
                self._event_artists.append(line)
        self.draw_idle()

    @staticmethod
    def _autoscale(ax, xs: Sequence[float], ys: Sequence[float]) -> None:
        if not xs:
            return
        ax.set_xlim(xs[0], xs[-1] if xs[-1] > xs[0] else xs[0] + 1.0)
        lo, hi = min(ys), max(ys)
        if hi <= lo:
            hi, lo = lo + 1.0, lo - 1.0
        pad = (hi - lo) * 0.12
        ax.set_ylim(lo - pad, hi + pad)
