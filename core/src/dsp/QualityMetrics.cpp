// core/src/dsp/QualityMetrics.cpp
// Implementation of compute_quality_metrics and quality_label.
// Ported from quality.py.
// Pure C++17, no Qt, no OS. All computations in double.

#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/dsp/ChannelSelect.h"
#include "ads1292/dsp/Quality.h"

#include <algorithm>
#include <cstddef>

namespace ads1292::dsp {

// ─── quality_label ───────────────────────────────────────────────────────────
std::string quality_label(const QualityMetrics& m)
{
    // Priority order matching quality.py:
    // 1. Bad contact or QRS not clear
    if (m.contact_ok_percent < 95.0 || !m.qrs_clear) {
        return "Needs review";
    }
    // 2. Too few beats or invalid HR
    if (m.r_peaks < 5 || m.hr_median_bpm <= 0.0) {
        return "Insufficient ECG";
    }
    // 3. Excellent contact + clear QRS
    if (m.contact_ok_percent >= 99.0 && m.qrs_clear) {
        return "Good ECG/QRS";
    }
    return "Usable ECG/QRS";
}

QualityMetrics compute_quality_metrics(
    const std::vector<ads1292::StreamSample>& samples,
    double sample_rate_hz,
    const std::string& source)
{
    // Empty guard — matches Python's early return for empty input.
    if (samples.empty()) {
        return QualityMetrics{
            0, 0.0, "CH1",
            0.0, 0, 0,
            0.0, 0.0, 0.0,
            false, false, false,
            0.0, 0.0,
            0.0, 0.0, 0.0
        };
    }

    const std::size_t n = samples.size();

    // Build double arrays for ch1 and ch2.
    std::vector<double> ch1(n), ch2(n);
    for (std::size_t i = 0; i < n; ++i) {
        ch1[i] = static_cast<double>(samples[i].ch1);
        ch2[i] = static_cast<double>(samples[i].ch2);
    }

    // Channel-selection + peaks/HR/PQRST in one call.
    ReviewResult result = review_channels(ch1, ch2, sample_rate_hz, source);

    // Choose the ECG vector based on the selected channel.
    const std::vector<double>& ecg =
        (result.source.channel == "CH2") ? ch2 : ch1;

    // Count lead-off bad samples.
    int lead_bad = 0;
    for (const auto& s : samples) {
        if (s.lead_off_bits() != 0) ++lead_bad;
    }

    // Duration: (n-1)/sr, 0 for single sample.
    const double duration =
        (n > 1) ? static_cast<double>(n - 1) / sample_rate_hz : 0.0;

    // Signal-quality primitives on the chosen ECG channel.
    const double baseline = baseline_drift(ecg, sample_rate_hz);
    const double noise    = noise_rms(ecg);
    double p2p = 0.0;
    if (!ecg.empty()) {
        const auto [lo, hi] = std::minmax_element(ecg.begin(), ecg.end());
        p2p = *hi - *lo;
    }

    // Contact quality.
    const double contact_ok =
        100.0 * static_cast<double>(n - static_cast<std::size_t>(lead_bad))
        / static_cast<double>(n);

    return QualityMetrics{
        static_cast<int>(n),
        duration,
        result.source.channel,
        contact_ok,
        lead_bad,
        static_cast<int>(result.peaks.size()),
        result.heart_rate.median_bpm,
        result.heart_rate.min_bpm,
        result.heart_rate.max_bpm,
        result.pqrst.qrs_clear,
        result.pqrst.p_tentative,
        result.pqrst.t_tentative,
        result.source.score_ch1,
        result.source.score_ch2,
        baseline,
        noise,
        p2p
    };
}

} // namespace ads1292::dsp
