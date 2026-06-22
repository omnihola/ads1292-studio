"""Review-side analysis panels: PQRST average beat, spectrum, and event log.

Each reuses the existing compute functions (signal_processing, spectrum) and
embeds matplotlib via FigureCanvasQTAgg, matching the live panel's styling.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg")
import numpy as np  # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from PySide6.QtWidgets import QPlainTextEdit  # noqa: E402

from ads1292_studio.signal_processing import pqrst_review, review_channels  # noqa: E402
from ads1292_studio.spectrum import build_spectrum_analysis  # noqa: E402
from ads1292_studio.ui_qt.tokens import design_tokens  # noqa: E402

_T = design_tokens()


def _style(ax) -> None:
    ax.set_facecolor(_T["panel_alt"])
    ax.grid(True, color=_T["border"], linewidth=0.6, alpha=0.8)
    for spine in ax.spines.values():
        spine.set_color(_T["border"])
    ax.tick_params(colors=_T["ink_faint"], labelsize=7)


def _empty(ax, canvas, msg: str) -> None:
    ax.clear()
    _style(ax)
    ax.text(0.5, 0.5, msg, transform=ax.transAxes, ha="center", va="center",
            color=_T["ink_faint"], fontsize=11, fontweight="bold")
    canvas.draw_idle()


class PqrstPanel(FigureCanvasQTAgg):
    """R-aligned average beat (PQRST)."""

    def __init__(self) -> None:
        fig = Figure(figsize=(7, 4), facecolor=_T["panel"])
        super().__init__(fig)
        self.ax = fig.add_subplot(111)
        fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.12)
        _style(self.ax)
        self.ax.set_xlabel("Time relative to R peak (ms)", fontsize=8)
        self.ax.set_ylabel("Filtered counts", fontsize=8)
        _empty(self.ax, self, "Load a CSV to view the PQRST average beat")

    def show_recording(self, samples, sample_rate_hz: float) -> None:
        ch1 = np.asarray([s.ch1 for s in samples], dtype=float)
        ch2 = np.asarray([s.ch2 for s in samples], dtype=float)
        review = review_channels(ch1, ch2, sample_rate_hz=sample_rate_hz, source="Auto")
        ecg = ch2 if review.source.channel == "CH2" else ch1
        pq = pqrst_review(ecg, review.peaks, sample_rate_hz)
        self.ax.clear()
        _style(self.ax)
        self.ax.set_xlabel("Time relative to R peak (ms)", fontsize=8)
        self.ax.set_ylabel("Filtered counts", fontsize=8)
        self._draw_beat(pq, review.source.channel)

    def render_recording(self, samples, sample_rate_hz: float, ecg_source: str | None = None) -> None:
        """Uniform renderer interface (RecordingRenderer)."""
        self.show_recording(samples, sample_rate_hz)

    def _draw_beat(self, pq, source_channel: str) -> None:
        if pq.average_beat:
            self.ax.plot(pq.time_ms, pq.average_beat, color=_T["ecg"], linewidth=1.4)
            self.ax.axvline(0, color=_T["bad"], linewidth=1.0, linestyle="--")
            self.ax.set_title(
                f"PQRST · QRS={pq.qrs_clear} · beats={pq.beats_used} · source {source_channel}",
                loc="left", fontsize=9, color=_T["ink"],
            )
        else:
            self.ax.text(0.5, 0.5, "No clean beats detected", transform=self.ax.transAxes,
                         ha="center", va="center", color=_T["ink_faint"], fontsize=11)
        self.draw_idle()


class SpectrumPanel(FigureCanvasQTAgg):
    """ECG power spectrum (top) and amplitude histogram (bottom)."""

    def __init__(self) -> None:
        fig = Figure(figsize=(7, 4), facecolor=_T["panel"])
        super().__init__(fig)
        self.ax_fft = fig.add_subplot(211)
        self.ax_hist = fig.add_subplot(212)
        fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.11, hspace=0.45)
        for ax in (self.ax_fft, self.ax_hist):
            _style(ax)
        self.ax_fft.set_ylabel("Power", fontsize=8)
        self.ax_hist.set_ylabel("Samples", fontsize=8)
        _empty(self.ax_fft, self, "Load a CSV to view the spectrum")

    def render_recording(self, samples, sample_rate_hz: float, ecg_source: str | None = None) -> None:
        """Uniform renderer interface (RecordingRenderer)."""
        self.show_recording(samples, ecg_source or "Auto", sample_rate_hz)

    def show_recording(self, samples, source: str, sample_rate_hz: float) -> None:
        analysis = build_spectrum_analysis(samples, source=source, sample_rate_hz=sample_rate_hz)
        self.ax_fft.clear()
        self.ax_hist.clear()
        for ax in (self.ax_fft, self.ax_hist):
            _style(ax)
        self.ax_fft.set_xlabel("Frequency (Hz)", fontsize=8)
        self.ax_fft.set_ylabel("Power", fontsize=8)
        self.ax_hist.set_xlabel("Raw counts", fontsize=8)
        self.ax_hist.set_ylabel("Samples", fontsize=8)
        if analysis.ecg_frequency_hz.size:
            self.ax_fft.plot(analysis.ecg_frequency_hz, analysis.ecg_power, color=_T["ecg"], linewidth=1.0)
            self.ax_fft.set_title(f"Power spectrum · {analysis.ecg_label}", loc="left", fontsize=9, color=_T["ink"])
        if analysis.histogram_counts.size:
            edges = analysis.histogram_bin_edges
            centers = (edges[:-1] + edges[1:]) / 2.0
            width = (edges[1] - edges[0]) if edges.size > 1 else 1.0
            self.ax_hist.bar(centers, analysis.histogram_counts, width=width, color=_T["resp"], alpha=0.85)
        self.draw_idle()


class EventLogPanel(QPlainTextEdit):
    """Read-only runtime log + event annotations."""

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)
        self.setPlaceholderText("Runtime log and event annotations appear here.")

    def append_line(self, line: str) -> None:
        self.appendPlainText(line)

    def set_events(self, events: list[dict]) -> None:
        if not events:
            return
        self.appendPlainText("— events —")
        for i, ev in enumerate(events, 1):
            if ev.get("kind") == "range":
                self.appendPlainText(f"  {i}. [range] {ev.get('label','')} {ev.get('start',0):.2f}–{ev.get('end',0):.2f}s")
            else:
                self.appendPlainText(f"  {i}. [point] {ev.get('label','')} @ {ev.get('t',0):.2f}s")


class RecordingInfoPanel(QPlainTextEdit):
    """Detailed, structured per-recording metrics (scientific review)."""

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self._uv_per_count: float | None = None
        self.setPlaceholderText("Load a CSV or finish a recording to see the detailed metrics report.")

    def set_calibration(self, uv_per_count: float | None) -> None:
        """Store calibration factor; applied on next render_recording call."""
        self._uv_per_count = uv_per_count

    def render_recording(self, samples, sample_rate_hz: float, ecg_source: str | None = None) -> None:
        from ads1292_studio.quality import compute_quality_metrics

        m = compute_quality_metrics(tuple(samples), sample_rate_hz=sample_rate_hz)
        uv = self._uv_per_count

        def _ct(counts: float) -> str:
            if uv is not None:
                return f"{counts:.1f} ct  ({counts * uv:.1f} µV)"
            return f"{counts:.1f} ct"

        cal_line = (
            f"  calibration       : {uv:.4g} µV/ct" if uv is not None
            else "  calibration       : not applied (raw counts)"
        )
        lines = [
            "RECORDING SUMMARY",
            f"  samples           : {m.sample_count}",
            f"  duration          : {m.duration_seconds:.3f} s  @ {sample_rate_hz:.0f} Hz",
            f"  ECG source        : {m.ecg_source}",
            f"  quality label     : {m.quality_label}",
            cal_line,
            "",
            "CONTACT / RATE",
            f"  contact OK        : {m.contact_ok_percent:.2f}%  ({m.lead_off_bad_samples} bad samples)",
            f"  R peaks           : {m.r_peaks}",
            f"  HR median/min/max : {m.hr_median_bpm:.1f} / {m.hr_min_bpm:.1f} / {m.hr_max_bpm:.1f} bpm",
            "",
            "MORPHOLOGY / ARTIFACTS",
            f"  QRS clear         : {m.qrs_clear}",
            f"  P / T tentative   : {m.p_tentative} / {m.t_tentative}",
            f"  baseline drift    : {_ct(m.baseline_drift_counts)}",
            f"  noise RMS         : {_ct(m.noise_rms_counts)}",
            f"  peak-to-peak      : {_ct(m.peak_to_peak_counts)}",
            f"  channel scores    : CH1={m.score_ch1:.3f}   CH2={m.score_ch2:.3f}",
        ]
        self.setPlainText("\n".join(lines))
