// core/src/index/SessionIndexRow.cpp
#include "ads1292/index/SessionIndexRow.h"
#include <cmath>
#include <numeric>

namespace ads1292 {
namespace index {

std::string status_for_quality(const std::string& quality_label) {
    if (quality_label == "Good ECG/QRS" || quality_label == "Usable ECG/QRS")
        return "usable";
    return "review";
}

std::string package_ready_status(const std::string& waveform_status, const std::string& sidecar_status) {
    if (sidecar_status != "complete")
        return "incomplete_record";
    if (waveform_status != "usable")
        return "needs_signal_review";
    return "package_ready";
}

std::string next_action(const std::string& pkg_ready_status) {
    if (pkg_ready_status == "package_ready")
        return "package_record";
    if (pkg_ready_status == "needs_signal_review")
        return "review_signal";
    return "complete_sidecars";
}

SessionIndexSummary summarize_rows(const std::vector<SessionIndexRow>& rows) {
    SessionIndexSummary s;
    s.recordings = static_cast<int>(rows.size());
    double total_annotated_seconds_sum = 0.0;
    for (const auto& row : rows) {
        if (row.status == "usable") ++s.usable_recordings;
        if (row.package_ready_status == "package_ready") ++s.package_ready;
        if (row.package_ready_status == "incomplete_record") ++s.incomplete_records;
        if (row.package_ready_status == "needs_signal_review") ++s.needs_signal_review;
        if (row.completion_status == "finalized") ++s.finalized_recordings;
        if (row.completion_status == "open") ++s.open_recordings;
        if (row.completion_status == "unknown") ++s.unknown_completion_records;
        if (row.completion_audit == "pass") ++s.completion_audit_pass;
        if (row.completion_audit == "fail") ++s.completion_audit_fail;
        if (row.completion_audit == "pending") ++s.completion_audit_pending;
        if (row.completion_audit == "unknown") ++s.completion_audit_unknown;
        if (row.recording_manifest_status == "pass") ++s.recording_manifest_pass;
        if (row.recording_manifest_status == "fail") ++s.recording_manifest_fail;
        if (row.recording_manifest_status == "missing") ++s.recording_manifest_missing;
        if (row.recording_manifest_status == "unknown") ++s.recording_manifest_unknown;
        if (row.event_count > 0) ++s.annotated_recordings;
        s.event_annotations += row.event_count;
        s.interval_event_annotations += row.interval_event_count;
        total_annotated_seconds_sum += row.total_annotated_seconds;
        s.total_annotated_samples += row.total_annotated_samples;
        if (row.next_action == "package_record") ++s.action_package_record;
        if (row.next_action == "complete_sidecars") ++s.action_complete_sidecars;
        if (row.next_action == "review_signal") ++s.action_review_signal;
    }
    // round to 6 decimal places
    s.total_annotated_seconds = std::round(total_annotated_seconds_sum * 1e6) / 1e6;
    return s;
}

}  // namespace index
}  // namespace ads1292
