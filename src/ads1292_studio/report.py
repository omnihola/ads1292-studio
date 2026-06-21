from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from ads1292_studio.matplotlib_runtime import configure_matplotlib_cache

configure_matplotlib_cache()

import matplotlib
import numpy as np

matplotlib.use("Agg")

from ads1292_studio.calibration import Calibration, counts_to_microvolts
from ads1292_studio.events import EventMarker
from ads1292_studio.models import PqrstReview, StreamSample
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.plot_theme import (
    PLOT_TRACE_COLORS,
    new_export_figure,
    plot_trace_styles,
    pqrst_plot_style,
    style_export_axes,
)
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality import QualityMetrics, compute_quality_metrics
from ads1292_studio.quality_gate import QualityGate, QualityGateResult, evaluate_quality_gate
from ads1292_studio.segments import (
    SegmentMetrics,
    SegmentQualityGateResult,
    analyze_protocol_segments,
    evaluate_segment_quality_gates,
)
from ads1292_studio.signal_processing import bandpass, detect_r_peaks, pqrst_review
from ads1292_studio.spectrum import build_spectrum_analysis


@dataclass(frozen=True)
class ReportExport:
    html_path: Path
    ecg_png_path: Path
    pqrst_png_path: Path
    spectrum_png_path: Path
    metrics: QualityMetrics
    segment_metrics: tuple[SegmentMetrics, ...] = tuple()
    segment_gate_result: SegmentQualityGateResult | None = None


def export_review_report(
    samples: tuple[StreamSample, ...] | list[StreamSample],
    out_dir: Path | str,
    title: str = "ADS1292 Studio Review",
    sample_rate_hz: float = 500.0,
    source: str = "Auto",
    metadata: SessionMetadata | None = None,
    events: tuple[EventMarker, ...] | list[EventMarker] | None = None,
    calibration: Calibration | None = None,
    quality_gate: QualityGate | None = None,
    protocol: TestProtocol | None = None,
) -> ReportExport:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    sample_tuple = tuple(samples)
    metrics = compute_quality_metrics(sample_tuple, sample_rate_hz=sample_rate_hz, source=source)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = _slugify(title)
    ecg_png = output / f"{stamp}-{slug}-ecg.png"
    pqrst_png = output / f"{stamp}-{slug}-pqrst.png"
    spectrum_png = output / f"{stamp}-{slug}-spectrum.png"
    html_path = output / f"{stamp}-{slug}.html"
    normalized_calibration = (calibration or Calibration()).normalized()
    gate_result = evaluate_quality_gate(metrics, quality_gate)
    segment_source = metrics.ecg_source if source == "Auto" else source
    segment_metrics = (
        analyze_protocol_segments(sample_tuple, protocol, sample_rate_hz=sample_rate_hz, source=segment_source)
        if protocol is not None
        else tuple()
    )
    segment_gate_result = evaluate_segment_quality_gates(segment_metrics, quality_gate) if segment_metrics else None
    _write_ecg_png(sample_tuple, ecg_png, metrics, sample_rate_hz, normalized_calibration)
    _write_pqrst_png(sample_tuple, pqrst_png, metrics, sample_rate_hz, normalized_calibration)
    _write_spectrum_png(sample_tuple, spectrum_png, metrics, sample_rate_hz)
    html_path.write_text(
        _html(
            title,
            metrics,
            ecg_png.name,
            pqrst_png.name,
            spectrum_png.name,
            metadata,
            tuple(events or ()),
            normalized_calibration,
            gate_result,
            protocol,
            segment_metrics,
            segment_gate_result,
        )
    )
    return ReportExport(html_path, ecg_png, pqrst_png, spectrum_png, metrics, segment_metrics, segment_gate_result)


def _slugify(text: str) -> str:
    clean = "".join(char.lower() if char.isalnum() else "-" for char in text)
    return "-".join(part for part in clean.split("-") if part)[:48] or "ads1292-review"


def _selected_channel(samples: tuple[StreamSample, ...], source: str) -> np.ndarray:
    if source == "CH2":
        return np.array([sample.ch2 for sample in samples], dtype=float)
    return np.array([sample.ch1 for sample in samples], dtype=float)


def _other_channel(samples: tuple[StreamSample, ...], source: str) -> np.ndarray:
    if source == "CH2":
        return np.array([sample.ch1 for sample in samples], dtype=float)
    return np.array([sample.ch2 for sample in samples], dtype=float)


def _write_ecg_png(
    samples: tuple[StreamSample, ...],
    path: Path,
    metrics: QualityMetrics,
    sample_rate_hz: float,
    calibration: Calibration,
) -> None:
    ecg_raw = _selected_channel(samples, metrics.ecg_source)
    other_raw = _other_channel(samples, metrics.ecg_source)
    ecg = counts_to_microvolts(bandpass(ecg_raw, sample_rate_hz), calibration)
    other = counts_to_microvolts(bandpass(other_raw, sample_rate_hz), calibration)
    peaks = detect_r_peaks(ecg_raw, sample_rate_hz)
    x = np.arange(ecg.size) / sample_rate_hz
    trace_styles = plot_trace_styles()
    fig = new_export_figure(figsize=(12, 7), dpi=160)
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212, sharex=ax1)
    ax1.plot(x, ecg, color=PLOT_TRACE_COLORS["ecg"], **trace_styles["ecg"])
    if peaks:
        ax1.plot(x[list(peaks)], ecg[list(peaks)], color=PLOT_TRACE_COLORS["peak"], **trace_styles["peak"])
    ax1.set_title(f"ECG source {metrics.ecg_source} | HR {metrics.hr_median_bpm:.1f} bpm | {metrics.quality_label}")
    ax1.set_ylabel("Filtered uV")
    ax2.plot(x, other, color=PLOT_TRACE_COLORS["respiration"], **trace_styles["respiration"])
    ax2.set_title("Other channel")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Filtered uV")
    style_export_axes((ax1, ax2))
    fig.tight_layout()
    fig.savefig(path)


def _write_pqrst_png(
    samples: tuple[StreamSample, ...],
    path: Path,
    metrics: QualityMetrics,
    sample_rate_hz: float,
    calibration: Calibration,
) -> None:
    ecg_raw = _selected_channel(samples, metrics.ecg_source)
    peaks = detect_r_peaks(ecg_raw, sample_rate_hz)
    review = pqrst_review(ecg_raw, peaks, sample_rate_hz)
    fig = new_export_figure(figsize=(10, 5), dpi=160)
    ax = fig.add_subplot(111)
    if review.average_beat:
        style = pqrst_plot_style()
        ax.plot(
            review.time_ms,
            counts_to_microvolts(np.asarray(review.average_beat, dtype=float), calibration),
            color=PLOT_TRACE_COLORS["ecg"],
            **style["average"],
        )
        ax.axvline(0, color=PLOT_TRACE_COLORS["peak"], **style["r_marker"])
        ax.axvspan(
            style["p_search"]["start_ms"],
            style["p_search"]["end_ms"],
            color=style["p_search"]["color"],
            alpha=style["p_search"]["alpha"],
            label=style["p_search"]["label"],
        )
        ax.axvspan(
            style["t_search"]["start_ms"],
            style["t_search"]["end_ms"],
            color=style["t_search"]["color"],
            alpha=style["t_search"]["alpha"],
            label=style["t_search"]["label"],
        )
        ax.legend(**style["legend"])
    ax.set_title(pqrst_review_title(review))
    ax.set_xlabel("Time relative to R peak (ms)")
    ax.set_ylabel("Filtered uV")
    style_export_axes((ax,))
    fig.tight_layout()
    fig.savefig(path)


def pqrst_review_title(review: PqrstReview) -> str:
    return (
        "PQRST review | "
        f"QRS={review.qrs_clear} | "
        f"P tentative={review.p_tentative} | "
        f"T tentative={review.t_tentative}"
    )


def _write_spectrum_png(
    samples: tuple[StreamSample, ...],
    path: Path,
    metrics: QualityMetrics,
    sample_rate_hz: float,
) -> None:
    analysis = build_spectrum_analysis(samples, source=metrics.ecg_source, sample_rate_hz=sample_rate_hz)
    fig = new_export_figure(figsize=(10, 6), dpi=160)
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212)
    trace_styles = plot_trace_styles()
    if analysis.ecg_frequency_hz.size:
        ax1.plot(
            analysis.ecg_frequency_hz,
            analysis.ecg_power,
            color=PLOT_TRACE_COLORS["ecg"],
            **trace_styles["ecg"],
        )
    if analysis.histogram_counts.size:
        widths = np.diff(analysis.histogram_bin_edges)
        ax2.bar(
            analysis.histogram_bin_edges[:-1],
            analysis.histogram_counts,
            width=widths,
            align="edge",
            color=PLOT_TRACE_COLORS["respiration"],
            alpha=0.72,
            linewidth=0,
        )
    ax1.set_title(f"FFT spectrum: {analysis.ecg_label}")
    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Power")
    ax2.set_title(f"Amplitude histogram: {analysis.ecg_label} raw counts")
    ax2.set_xlabel("Raw counts")
    ax2.set_ylabel("Samples")
    style_export_axes((ax1, ax2))
    fig.tight_layout()
    fig.savefig(path)


def _event_row(event: EventMarker) -> str:
    marker = event.normalized()
    return (
        "<tr>"
        f"<td>{marker.timestamp_seconds:.2f}</td>"
        f"<td>{marker.end_seconds:.2f}</td>"
        f"<td>{marker.duration_seconds:.2f}</td>"
        f"<td>{escape(marker.label)}</td>"
        f"<td>{escape(marker.notes)}</td>"
        "</tr>"
    )


def _html(
    title: str,
    metrics: QualityMetrics,
    ecg_png: str,
    pqrst_png: str,
    spectrum_png: str,
    metadata: SessionMetadata | None,
    events: tuple[EventMarker, ...],
    calibration: Calibration,
    gate_result: QualityGateResult,
    protocol: TestProtocol | None,
    segment_metrics: tuple[SegmentMetrics, ...],
    segment_gate_result: SegmentQualityGateResult | None,
) -> str:
    rows = [
        ("Quality", metrics.quality_label),
        ("ECG source", metrics.ecg_source),
        ("Samples", str(metrics.sample_count)),
        ("Duration", f"{metrics.duration_seconds:.2f} s"),
        ("Contact OK", f"{metrics.contact_ok_percent:.2f}%"),
        ("Lead-off bad samples", str(metrics.lead_off_bad_samples)),
        ("R peaks", str(metrics.r_peaks)),
        ("Median HR", f"{metrics.hr_median_bpm:.1f} bpm"),
        ("HR range", f"{metrics.hr_min_bpm:.1f}-{metrics.hr_max_bpm:.1f} bpm"),
        ("QRS clear", str(metrics.qrs_clear)),
        ("P wave", "tentative" if metrics.p_tentative else "not reliable"),
        ("T wave", "tentative" if metrics.t_tentative else "not reliable"),
        ("Baseline drift", f"{metrics.baseline_drift_counts:.1f} counts"),
        ("Noise RMS", f"{metrics.noise_rms_counts:.1f} counts"),
        ("Peak-to-peak", f"{metrics.peak_to_peak_counts:.1f} counts"),
        ("CH1 score", f"{metrics.score_ch1:.2f}"),
        ("CH2 score", f"{metrics.score_ch2:.2f}"),
    ]
    table = "\n".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in rows)
    metadata_html = ""
    if metadata is not None:
        meta = metadata.normalized()
        meta_rows = [
            ("Session ID", meta.session_id),
            ("Subject ID", meta.subject_id),
            ("Electrode", meta.electrode),
            ("Montage", meta.montage),
            ("Operator", meta.operator),
            ("Notes", meta.notes),
        ]
        metadata_table = "\n".join(
            f"<tr><th>{escape(key)}</th><td>{escape(value)}</td></tr>" for key, value in meta_rows
        )
        metadata_html = f"<h2>Session Metadata</h2><table>{metadata_table}</table>"
    events_html = ""
    if events:
        event_rows = "\n".join(
            _event_row(event)
            for event in events
        )
        events_html = (
            "<h2>Event Markers</h2>"
            "<table><tr><th>Start (s)</th><th>End (s)</th><th>Duration (s)</th><th>Label</th><th>Notes</th></tr>"
            f"{event_rows}</table>"
        )
    protocol_html = ""
    if protocol is not None:
        normalized_protocol = protocol.normalized()
        step_rows = "\n".join(
            "<tr>"
            f"<td>{step.start_seconds:.2f}</td>"
            f"<td>{step.duration_seconds:.2f}</td>"
            f"<td>{escape(step.label)}</td>"
            f"<td>{escape(step.instruction)}</td>"
            "</tr>"
            for step in normalized_protocol.steps
        )
        protocol_html = (
            "<h2>Test Protocol</h2>"
            "<table>"
            f"<tr><th>Name</th><td>{escape(normalized_protocol.name)}</td></tr>"
            f"<tr><th>Objective</th><td>{escape(normalized_protocol.objective)}</td></tr>"
            f"<tr><th>Operator instructions</th><td>{escape(normalized_protocol.operator_instructions)}</td></tr>"
            f"<tr><th>Acceptance notes</th><td>{escape(normalized_protocol.acceptance_notes)}</td></tr>"
            "</table>"
            "<table><tr><th>Start (s)</th><th>Duration (s)</th><th>Label</th><th>Instruction</th></tr>"
            f"{step_rows}</table>"
        )
    segment_html = ""
    if segment_metrics:
        segment_rows = "\n".join(
            "<tr>"
            f"<td>{escape(segment.label)}</td>"
            f"<td>{segment.start_seconds:.2f}</td>"
            f"<td>{segment.duration_seconds:.2f}</td>"
            f"<td>{segment.sample_count}</td>"
            f"<td>{escape(segment.ecg_source)}</td>"
            f"<td>{segment.contact_ok_percent:.2f}%</td>"
            f"<td>{segment.r_peaks}</td>"
            f"<td>{segment.hr_median_bpm:.1f}</td>"
            f"<td>{segment.baseline_drift_counts:.1f}</td>"
            f"<td>{segment.noise_rms_counts:.1f}</td>"
            f"<td>{segment.peak_to_peak_counts:.1f}</td>"
            f"<td>{escape(segment.quality_label)}</td>"
            "</tr>"
            for segment in segment_metrics
        )
        segment_html = (
            "<h2>Protocol Segment Metrics</h2>"
            "<table><tr>"
            "<th>Label</th><th>Start (s)</th><th>Duration (s)</th><th>Samples</th>"
            "<th>Source</th><th>Contact OK</th><th>R peaks</th><th>Median HR</th>"
            "<th>Baseline drift</th><th>Noise RMS</th><th>Peak-to-peak</th><th>Quality</th>"
            "</tr>"
            f"{segment_rows}</table>"
        )
    segment_gate_html = ""
    if segment_gate_result is not None:
        gate_rows = "\n".join(
            "<tr>"
            f"<td>{escape(result.label)}</td>"
            f"<td>{escape(result.status)}</td>"
            f"<td>{escape('; '.join(result.failures) if result.failures else 'None')}</td>"
            "</tr>"
            for result in segment_gate_result.segment_results
        )
        segment_gate_html = (
            "<h2>Protocol Segment Gate</h2>"
            "<table>"
            f"<tr><th>Status</th><td>{escape(segment_gate_result.label)}</td></tr>"
            f"<tr><th>Failures</th><td>{escape('; '.join(segment_gate_result.failures) if segment_gate_result.failures else 'None')}</td></tr>"
            "</table>"
            "<table><tr><th>Segment</th><th>Status</th><th>Failures</th></tr>"
            f"{gate_rows}</table>"
        )
    calibration = calibration.normalized()
    calibration_rows = [
        ("Label", calibration.label),
        ("Reference voltage", f"{calibration.vref_mv / 1000.0:.3f} V"),
        ("PGA gain", f"{calibration.pga_gain:g}"),
        ("ADC bits", str(calibration.adc_bits)),
        ("ECG scale", f"{calibration.microvolts_per_count:.4f} uV/count"),
    ]
    calibration_table = "\n".join(
        f"<tr><th>{escape(key)}</th><td>{escape(value)}</td></tr>" for key, value in calibration_rows
    )
    calibration_html = f"<h2>Calibration</h2><table>{calibration_table}</table>"
    gate_rows = [
        ("Status", gate_result.label),
        ("Failures", "; ".join(gate_result.failures) if gate_result.failures else "None"),
    ]
    gate_table = "\n".join(f"<tr><th>{escape(key)}</th><td>{escape(value)}</td></tr>" for key, value in gate_rows)
    gate_html = f"<h2>Quality Gate</h2><table>{gate_table}</table>"
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; color: #1f2937; }}
    h1 {{ margin-bottom: 4px; }}
    .sub {{ color: #6b7280; margin-bottom: 24px; }}
    table {{ border-collapse: collapse; margin: 16px 0 28px; min-width: 420px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; }}
    th {{ background: #f3f4f6; }}
    img {{ max-width: 100%; border: 1px solid #e5e7eb; margin: 12px 0 24px; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <div class=\"sub\">Generated by ADS1292 Studio. Research use only; not diagnostic medical software.</div>
  {metadata_html}
  {protocol_html}
  {segment_html}
  {segment_gate_html}
  {events_html}
  {calibration_html}
  {gate_html}
  <h2>Signal Quality</h2>
  <table>{table}</table>
  <h2>ECG Review</h2>
  <p>Exported ECG and PQRST plots use a fixed QRS bandpass for review consistency; GUI display filter toggles are not applied to this report.</p>
  <img src=\"{escape(ecg_png)}\" alt=\"ECG review plot\">
  <h2>PQRST Review</h2>
  <img src=\"{escape(pqrst_png)}\" alt=\"PQRST review plot\">
  <h2>FFT / Histogram</h2>
  <p>FFT and amplitude histogram are computed from the raw selected ECG channel for exploratory signal review.</p>
  <img src=\"{escape(spectrum_png)}\" alt=\"FFT spectrum and amplitude histogram\">
</body>
</html>
"""
