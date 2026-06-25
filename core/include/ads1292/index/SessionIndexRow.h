#pragma once
// core/include/ads1292/index/SessionIndexRow.h
// Pure C++17 — no Qt, no nlohmann.
#include <string>
#include <vector>

namespace ads1292 {
namespace index {

struct SessionIndexRow {
    std::string path;
    std::string relative_path;
    std::string session_id;
    std::string subject_id;
    std::string electrode;
    std::string montage;
    std::string operator_;  // JSON key is "operator" (C++ keyword avoided)
    int         sample_count          = 0;
    double      duration_seconds      = 0.0;
    std::string completion_status;
    int         recorded_sample_count = 0;
    double      recorded_span_seconds = 0.0;
    std::string completion_audit;
    int         recorded_sample_count_delta = 0;
    double      recorded_span_delta_seconds = 0.0;
    std::string ecg_source;
    double      contact_ok_percent    = 0.0;
    int         r_peaks               = 0;
    double      hr_median_bpm         = 0.0;
    bool        qrs_clear             = false;
    std::string quality_label;
    std::string status;
    std::string sidecar_status;
    std::string missing_sidecars;
    int         event_count           = 0;
    int         interval_event_count  = 0;
    double      total_annotated_seconds = 0.0;
    int         total_annotated_samples = 0;
    std::string event_labels;
    std::string recording_manifest_status;
    std::string recording_manifest_failures;
    std::string package_ready_status;
    std::string next_action;
};

struct SessionIndexSummary {
    int    recordings                  = 0;
    int    usable_recordings           = 0;
    int    package_ready               = 0;
    int    incomplete_records          = 0;
    int    needs_signal_review         = 0;
    int    finalized_recordings        = 0;
    int    open_recordings             = 0;
    int    unknown_completion_records  = 0;
    int    completion_audit_pass       = 0;
    int    completion_audit_fail       = 0;
    int    completion_audit_pending    = 0;
    int    completion_audit_unknown    = 0;
    int    recording_manifest_pass     = 0;
    int    recording_manifest_fail     = 0;
    int    recording_manifest_missing  = 0;
    int    recording_manifest_unknown  = 0;
    int    annotated_recordings        = 0;
    int    event_annotations           = 0;
    int    interval_event_annotations  = 0;
    double total_annotated_seconds     = 0.0;
    int    total_annotated_samples     = 0;
    int    action_package_record       = 0;
    int    action_complete_sidecars    = 0;
    int    action_review_signal        = 0;
};

/// Derivation helpers (match session_index.py exactly).
std::string status_for_quality(const std::string& quality_label);
std::string package_ready_status(const std::string& waveform_status, const std::string& sidecar_status);
std::string next_action(const std::string& pkg_ready_status);

/// Aggregate a list of rows into a summary (24 counters).
SessionIndexSummary summarize_rows(const std::vector<SessionIndexRow>& rows);

}  // namespace index
}  // namespace ads1292
