from pathlib import Path

import numpy as np

from ads1292_studio.models import StreamSample
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


def test_quality_metrics_include_contact_hr_and_source() -> None:
    metrics = compute_quality_metrics(synthetic_samples())

    assert metrics.ecg_source == "CH2"
    assert metrics.contact_ok_percent > 99
    assert 95 <= metrics.hr_median_bpm <= 110
    assert metrics.qrs_clear is True
    assert metrics.r_peaks >= 10


def test_export_review_report_writes_html_and_png(tmp_path: Path) -> None:
    result = export_review_report(
        samples=synthetic_samples(),
        out_dir=tmp_path,
        title="Synthetic ADS1292 Review",
    )

    assert result.html_path.exists()
    assert result.ecg_png_path.exists()
    assert result.pqrst_png_path.exists()
    html = result.html_path.read_text()
    assert "Synthetic ADS1292 Review" in html
    assert "ECG source" in html
    assert "CH2" in html
    assert "QRS" in html
