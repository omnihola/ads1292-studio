from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ads1292_studio.models import StreamSample


@dataclass(frozen=True)
class SpectrumAnalysis:
    ecg_label: str
    ecg_frequency_hz: np.ndarray
    ecg_power: np.ndarray
    histogram_counts: np.ndarray
    histogram_bin_edges: np.ndarray


def build_spectrum_analysis(
    samples: tuple[StreamSample, ...] | list[StreamSample],
    *,
    source: str,
    sample_rate_hz: float,
    max_frequency_hz: float = 60.0,
    histogram_bins: int = 48,
) -> SpectrumAnalysis:
    values = _selected_channel(tuple(samples), source)
    if values.size == 0:
        empty = np.array([], dtype=float)
        return SpectrumAnalysis(str(source), empty, empty, np.array([], dtype=int), empty)
    frequencies, power = _fft_power(values, sample_rate_hz, max_frequency_hz)
    counts, edges = np.histogram(values, bins=max(1, int(histogram_bins)))
    return SpectrumAnalysis(
        ecg_label=str(source),
        ecg_frequency_hz=frequencies,
        ecg_power=power,
        histogram_counts=counts,
        histogram_bin_edges=edges,
    )


def _selected_channel(samples: tuple[StreamSample, ...], source: str) -> np.ndarray:
    if source == "CH1":
        return np.asarray([sample.ch1 for sample in samples], dtype=float)
    return np.asarray([sample.ch2 for sample in samples], dtype=float)


def _fft_power(values: np.ndarray, sample_rate_hz: float, max_frequency_hz: float) -> tuple[np.ndarray, np.ndarray]:
    # Guard before np.mean: an empty array would otherwise warn ("Mean of empty
    # slice") and center on NaN before this check could return.
    if values.size < 2:
        return np.array([], dtype=float), np.array([], dtype=float)
    centered = values - np.mean(values)
    window = np.hanning(centered.size)
    spectrum = np.fft.rfft(centered * window)
    frequencies = np.fft.rfftfreq(centered.size, d=1.0 / float(sample_rate_hz))
    power = np.abs(spectrum) ** 2
    keep = frequencies <= float(max_frequency_hz)
    return frequencies[keep], power[keep]
