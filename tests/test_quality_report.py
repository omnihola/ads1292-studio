from pathlib import Path

import numpy as np

from ads1292_studio.calibration import Calibration
from ads1292_studio.models import PqrstReview, StreamSample
from ads1292_studio.events import EventMarker
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.protocol import ProtocolStep, TestProtocol
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.quality import compute_quality_metrics
from ads1292_studio.report import export_review_report


def synthetic_samples(sample_rate_hz: float = 500.0) -> tuple[StreamSample, ...]:
    t = np.arange(0, 7, 1 / sample_rate_hz)
    ch1 = 20 * np.sin(2 * np.pi * 0.8 * t)
    ch2 = 10 * np.sin(2 * np.pi * 1.0 * t)
    for peak in np.arange(0.5, 6.8, 0.58):
        ch2 += 420 * np.exp(-0.5 * ((t - peak) / 0.012) ** 2)
    samples: list[StreamSample] = []
    for index, (one, two) in enumerate(zip(ch1, ch2)):
        samples.append(
            StreamSample(
                timestamp=index / sample_rate_hz,
                ch1=int(round(one)),
                ch2=int(round(two)),
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0 if index % 200 else 0x10,
            )
        )
    return tuple(samples)


def drifting_samples(sample_rate_hz: float = 500.0) -> tuple[StreamSample, ...]:
    t = np.arange(0, 8, 1 / sample_rate_hz)
    drift = 100 * (t / t[-1])
    ch2 = drift + 8 * np.sin(2 * np.pi * 1.0 * t)
    for peak in np.arange(0.5, 7.8, 0.62):
        ch2 += 450 * np.exp(-0.5 * ((t - peak) / 0.012) ** 2)
    return tuple(
        StreamSample(
            timestamp=index / sample_rate_hz,
            ch1=0,
            ch2=int(round(value)),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index, value in enumerate(ch2)
    )


def test_quality_metrics_include_contact_hr_and_source() -> None:
    metrics = compute_quality_metrics(synthetic_samples())

    assert metrics.ecg_source == "CH2"
    assert metrics.contact_ok_percent > 99
    assert 95 <= metrics.hr_median_bpm <= 110
    assert metrics.qrs_clear is True
    assert metrics.r_peaks >= 10


def test_quality_metrics_include_artifact_and_drift_values() -> None:
    metrics = compute_quality_metrics(drifting_samples())

    assert metrics.baseline_drift_counts >= 80
    assert metrics.noise_rms_counts > 0
    assert metrics.peak_to_peak_counts > 400


def test_export_review_report_writes_html_and_png(tmp_path: Path) -> None:
    result = export_review_report(
        samples=synthetic_samples(),
        out_dir=tmp_path,
        title="Synthetic ADS1292 Review",
        metadata=SessionMetadata(
            session_id="session-42",
            subject_id="anonymous-A",
            electrode="commercial Ag/AgCl",
            montage="RA/LA/RL torso",
            notes="no movement",
        ),
        events=(EventMarker(timestamp_seconds=2.5, duration_seconds=1.25, label="motion", notes="arm moved"),),
        calibration=Calibration(vref_mv=2420.0, pga_gain=6.0, adc_bits=24),
        quality_gate=QualityGate(min_duration_seconds=5.0),
        protocol=TestProtocol(
            name="Gel comparison protocol",
            objective="Compare MOTAC gel to commercial Ag/AgCl.",
            steps=(
                ProtocolStep(start_seconds=0.0, duration_seconds=3.0, label="baseline", instruction="Sit still."),
                ProtocolStep(start_seconds=3.0, duration_seconds=2.0, label="motion", instruction="Move arm."),
            ),
        ),
    )

    assert result.html_path.exists()
    assert result.ecg_png_path.exists()
    assert result.pqrst_png_path.exists()
    assert result.spectrum_png_path.exists()
    assert all(segment.ecg_source == result.metrics.ecg_source for segment in result.segment_metrics)
    html = result.html_path.read_text()
    assert "Synthetic ADS1292 Review" in html
    assert "ECG source" in html
    assert "CH2" in html
    assert "QRS" in html
    assert "session-42" in html
    assert "commercial Ag/AgCl" in html
    assert "Event Markers" in html
    assert "Duration (s)" in html
    assert "End (s)" in html
    assert "3.75" in html
    assert "motion" in html
    assert "arm moved" in html
    assert "Calibration" in html
    assert "2.420 V" in html
    assert "0.0481 uV/count" in html
    assert "Quality Gate" in html
    assert "Pass" in html
    assert "Test Protocol" in html
    assert "Gel comparison protocol" in html
    assert "baseline" in html
    assert "Protocol Segment Metrics" in html
    assert "Protocol Segment Gate" in html
    assert "motion" in html
    assert "Baseline drift" in html
    assert "Noise RMS" in html
    assert "Peak-to-peak" in html
    assert "fixed QRS bandpass" in html
    assert "FFT / Histogram" in html


def test_pqrst_report_title_marks_p_and_t_as_tentative() -> None:
    from ads1292_studio import report

    pqrst_review_title = getattr(report, "pqrst_review_title")
    title = pqrst_review_title(PqrstReview(True, True, True, 12, tuple(), tuple()))

    assert title == "PQRST review | QRS=True | P tentative=True | T tentative=True"
    assert "P=True" not in title
    assert "T=True" not in title
