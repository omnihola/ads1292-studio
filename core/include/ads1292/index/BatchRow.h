#pragma once
// core/include/ads1292/index/BatchRow.h
// Pure C++17 — no Qt, no nlohmann.
#include <string>
#include <vector>

namespace ads1292 {
namespace index {

/// Per-recording row produced by aggregate_recordings.
/// Fields match batch.py BatchRow exactly (15 fields).
struct BatchRow {
    std::string path;                 ///< Absolute path to the CSV file
    std::string session_id;
    std::string subject_id;
    std::string electrode;
    std::string montage;
    int         sample_count          = 0;
    double      duration_seconds      = 0.0;
    std::string ecg_source;
    double      contact_ok_percent    = 0.0;
    int         r_peaks               = 0;
    double      hr_median_bpm         = 0.0;
    bool        qrs_clear             = false;
    bool        p_tentative           = false;
    bool        t_tentative           = false;
    std::string quality_label;
};

/// Per-electrode group summary produced by group_recordings_by_electrode.
/// Fields match batch.py BatchGroupSummary exactly (8 fields).
struct BatchGroupSummary {
    std::string electrode;
    int         recordings            = 0;
    int         usable_recordings     = 0;
    double      usable_percent        = 0.0;
    double      mean_duration_seconds = 0.0;
    double      mean_contact_ok_percent = 0.0;
    double      mean_r_peaks          = 0.0;
    double      mean_hr_median_bpm    = 0.0;
};

/// Group rows by electrode, compute per-group means and usable counts.
/// Groups are ordered by electrode (sorted alphabetically), matching batch.py.
/// "usable" recordings are those whose quality_label is "Good ECG/QRS" or "Usable ECG/QRS".
std::vector<BatchGroupSummary> group_recordings_by_electrode(
    const std::vector<BatchRow>& rows);

}  // namespace index
}  // namespace ads1292
