#pragma once
// core/include/ads1292/dsp/QualityMetrics.h
// Full signal-quality summary: compute_quality_metrics.
// Pure C++17, no Qt, no OS. All computations in double.

#include "ads1292/model/StreamSample.h"

#include <string>
#include <vector>

namespace ads1292::dsp {

/// Full signal-quality summary for a recording segment.
struct QualityMetrics {
    int    sample_count;           ///< Total number of samples
    double duration_seconds;       ///< (sample_count - 1) / sample_rate_hz
    std::string ecg_source;        ///< "CH1" or "CH2" — the chosen ECG channel

    double contact_ok_percent;     ///< 100 * (samples with lead_off_bits()==0) / total
    int    lead_off_bad_samples;   ///< Count of samples where lead_off_bits() != 0

    int    r_peaks;                ///< Number of R-peaks detected

    double hr_median_bpm;          ///< Median HR from RR intervals
    double hr_min_bpm;             ///< Min HR from RR intervals
    double hr_max_bpm;             ///< Max HR from RR intervals

    bool   qrs_clear;              ///< From pqrst_review
    bool   p_tentative;            ///< From pqrst_review
    bool   t_tentative;            ///< From pqrst_review

    double score_ch1;              ///< qrs_like_score for CH1
    double score_ch2;              ///< qrs_like_score for CH2

    double baseline_drift_counts;  ///< baseline_drift on the chosen ECG channel
    double noise_rms_counts;       ///< noise_rms on the chosen ECG channel
    double peak_to_peak_counts;    ///< max(ecg) - min(ecg)
};

/// Returns a human-readable quality label for a QualityMetrics summary.
///
/// Algorithm (quality.py):
///   if contact_ok_percent < 95 || !qrs_clear  → "Needs review"
///   if r_peaks < 5 || hr_median_bpm <= 0       → "Insufficient ECG"
///   if contact_ok_percent >= 99 && qrs_clear   → "Good ECG/QRS"
///   else                                        → "Usable ECG/QRS"
std::string quality_label(const QualityMetrics& m);

/// Computes a full quality summary from a vector of StreamSamples.
///
/// Algorithm (per quality.py):
///   if samples.empty() → QualityMetrics{0, 0.0, "CH1", 0.0, 0, 0,
///                                        0.0, 0.0, 0.0, false, false, false,
///                                        0.0, 0.0, 0.0, 0.0, 0.0}
///   ch1[i] = (double)samples[i].ch1;  ch2[i] = (double)samples[i].ch2
///   result = review_channels(ch1, ch2, sample_rate_hz, source)
///   ecg = (result.source.channel == "CH2") ? ch2 : ch1
///   lead_bad = count of samples where s.lead_off_bits() != 0
///   duration = (size > 1) ? (size - 1) / sample_rate_hz : 0.0
///   baseline = baseline_drift(ecg, sample_rate_hz)
///   noise    = noise_rms(ecg)
///   p2p      = ecg.empty() ? 0.0 : max(ecg) - min(ecg)
///   contact_ok = 100.0 * (size - lead_bad) / size
QualityMetrics compute_quality_metrics(
    const std::vector<ads1292::StreamSample>& samples,
    double sample_rate_hz,
    const std::string& source);

} // namespace ads1292::dsp
