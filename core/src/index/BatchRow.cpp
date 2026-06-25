// core/src/index/BatchRow.cpp
// Pure C++17 — no Qt, no nlohmann.
#include "ads1292/index/BatchRow.h"

#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace ads1292 {
namespace index {

namespace {

/// Arithmetic mean rounded to 2 decimal places, matching batch.py _mean.
/// Returns 0.0 for empty input.
double _mean(const std::vector<double>& values) {
    if (values.empty()) return 0.0;
    double sum = 0.0;
    for (double v : values) sum += v;
    return std::round((sum / static_cast<double>(values.size())) * 100.0) / 100.0;
}

/// Whether a quality label counts as "usable" in batch.py.
/// Matches: item.quality_label in {"Good ECG/QRS", "Usable ECG/QRS"}
bool is_usable(const std::string& quality_label) {
    return quality_label == "Good ECG/QRS" || quality_label == "Usable ECG/QRS";
}

}  // anonymous namespace

// ── group_recordings_by_electrode ──────────────────────────────────────────
// Matches batch.py group_recordings_by_electrode exactly:
//   - insertion-order grouping with a dict, then iterate sorted(grouped)
//   - usable% = round(100.0 * usable / recordings, 2)
//   - means via _mean (round to 2dp)
std::vector<BatchGroupSummary> group_recordings_by_electrode(
    const std::vector<BatchRow>& rows)
{
    // Preserve insertion order for the set of electrodes seen.
    std::map<std::string, std::vector<const BatchRow*>> grouped;
    for (const auto& row : rows) {
        grouped[row.electrode].push_back(&row);
    }

    // Iterate in sorted electrode order (std::map is already sorted).
    std::vector<BatchGroupSummary> summaries;
    summaries.reserve(grouped.size());

    for (const auto& [electrode, items] : grouped) {
        int recordings = static_cast<int>(items.size());
        int usable = 0;
        std::vector<double> durations, contacts, r_peaks_v, hr_medians;
        durations.reserve(recordings);
        contacts.reserve(recordings);
        r_peaks_v.reserve(recordings);
        hr_medians.reserve(recordings);

        for (const BatchRow* item : items) {
            if (is_usable(item->quality_label)) ++usable;
            durations.push_back(item->duration_seconds);
            contacts.push_back(item->contact_ok_percent);
            r_peaks_v.push_back(static_cast<double>(item->r_peaks));
            hr_medians.push_back(item->hr_median_bpm);
        }

        double usable_percent = (recordings > 0)
            ? std::round(100.0 * usable / recordings * 100.0) / 100.0
            : 0.0;

        BatchGroupSummary s;
        s.electrode              = electrode;
        s.recordings             = recordings;
        s.usable_recordings      = usable;
        s.usable_percent         = usable_percent;
        s.mean_duration_seconds  = _mean(durations);
        s.mean_contact_ok_percent = _mean(contacts);
        s.mean_r_peaks           = _mean(r_peaks_v);
        s.mean_hr_median_bpm     = _mean(hr_medians);
        summaries.push_back(std::move(s));
    }

    return summaries;
}

}  // namespace index
}  // namespace ads1292
