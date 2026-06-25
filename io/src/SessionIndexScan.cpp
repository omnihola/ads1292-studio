// io/src/SessionIndexScan.cpp
#include "ads1292/io/SessionIndexScan.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/EventsIo.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/EventMarker.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using namespace ads1292::index;

namespace ads1292 {
namespace io {

namespace {

// ── _looks_like_recording_csv ──────────────────────────────────────────────
// Mirrors session_index.py: check stem and header columns.
bool _looks_like_recording_csv(const fs::path& path) {
    const std::string stem = path.stem().string();
    if (stem.find("session-index") != std::string::npos)
        return false;
    if (stem.size() >= 7 && stem.substr(stem.size() - 7) == "-groups")
        return false;
    // Read header line
    std::ifstream f(path);
    if (!f.is_open()) return false;
    std::string line;
    if (!std::getline(f, line)) return false;
    // strip \r
    if (!line.empty() && line.back() == '\r') line.pop_back();
    // split by comma
    std::set<std::string> fields;
    std::istringstream ss(line);
    std::string tok;
    while (std::getline(ss, tok, ',')) {
        if (!tok.empty() && tok.back() == '\r') tok.pop_back();
        fields.insert(tok);
    }
    bool has_timestamp = fields.count("timestamp") > 0;
    bool has_ch1 = fields.count("ch1_counts") > 0 || fields.count("ecg_counts") > 0;
    bool has_ch2 = fields.count("ch2_counts") > 0 || fields.count("resp_counts") > 0;
    return has_timestamp && has_ch1 && has_ch2;
}

// ── _metadata_for ─────────────────────────────────────────────────────────
// No bundle detection ported — just check <stem>.json sidecar.
ads1292::SessionMetadata _metadata_for(const fs::path& csv_path) {
    fs::path sidecar = fs::path(csv_path).replace_extension(".json");
    if (fs::exists(sidecar)) {
        try {
            return read_metadata_json(sidecar.string());
        } catch (...) {}
    }
    ads1292::SessionMetadata m;
    m.session_id = csv_path.stem().string();
    return m.normalized();
}

// ── _sidecar_status ────────────────────────────────────────────────────────
// Returns ("complete","") or ("missing","name1;name2;...")
std::pair<std::string, std::string> _sidecar_status(const fs::path& csv_path) {
    struct SidecarCheck {
        std::string name;
        std::vector<fs::path> paths;
    };
    std::vector<SidecarCheck> expected = {
        {"metadata",    {fs::path(csv_path).replace_extension(".json")}},
        {"events",      {fs::path(csv_path).replace_extension(".events.json"),
                         fs::path(csv_path).replace_extension(".events.csv")}},
        {"calibration", {fs::path(csv_path).replace_extension(".calibration.json")}},
        {"acquisition", {fs::path(csv_path).replace_extension(".acquisition.json")}},
        {"protocol",    {fs::path(csv_path).replace_extension(".protocol.json")}},
        {"quality_gate",{fs::path(csv_path).replace_extension(".quality-gate.json")}},
        {"processing",  {fs::path(csv_path).replace_extension(".processing.json")}},
    };
    std::vector<std::string> missing;
    for (const auto& sc : expected) {
        bool found = false;
        for (const auto& p : sc.paths) {
            if (fs::exists(p)) { found = true; break; }
        }
        if (!found) missing.push_back(sc.name);
    }
    if (missing.empty()) return {"complete", ""};
    std::string joined;
    for (size_t i = 0; i < missing.size(); ++i) {
        if (i > 0) joined += ";";
        joined += missing[i];
    }
    return {"missing", joined};
}

// ── EventAnnotationSummary ─────────────────────────────────────────────────
struct EventAnnotationSummary {
    int    count                   = 0;
    int    interval_count          = 0;
    double total_annotated_seconds = 0.0;
    int    total_annotated_samples = 0;
    std::string labels;
};

// ── _summarize_events ─────────────────────────────────────────────────────
// Mirrors session_index.py _summarize_events.
EventAnnotationSummary _summarize_events(
    const std::vector<ads1292::EventMarker>& events,
    double sample_rate_hz)
{
    std::map<std::string, int> label_counts;
    int interval_count = 0;
    double total_annotated_seconds = 0.0;
    int total_annotated_samples = 0;
    for (const auto& ev : events) {
        auto marker = ev.normalized();
        label_counts[marker.label]++;
        if (marker.duration_seconds > 0.0) {
            ++interval_count;
            total_annotated_seconds += marker.duration_seconds;
            // duration_samples = round(duration * sr)
            int dur_samples = static_cast<int>(std::round(marker.duration_seconds * sample_rate_hz));
            total_annotated_samples += dur_samples;
        }
    }
    // labels: sorted by label, "label:count;..."
    std::string label_text;
    bool first = true;
    for (const auto& kv : label_counts) {  // std::map is sorted
        if (!first) label_text += ";";
        label_text += kv.first + ":" + std::to_string(kv.second);
        first = false;
    }
    EventAnnotationSummary s;
    s.count = static_cast<int>(events.size());
    s.interval_count = interval_count;
    s.total_annotated_seconds = std::round(total_annotated_seconds * 1e6) / 1e6;
    s.total_annotated_samples = total_annotated_samples;
    s.labels = label_text;
    return s;
}

// ── _event_summary_for ────────────────────────────────────────────────────
EventAnnotationSummary _event_summary_for(const fs::path& csv_path, double sample_rate_hz) {
    fs::path events_json = fs::path(csv_path).replace_extension(".events.json");
    if (fs::exists(events_json)) {
        try {
            auto evs = read_events_json(events_json.string());
            return _summarize_events(evs, sample_rate_hz);
        } catch (...) {}
    }
    return EventAnnotationSummary{};
}

// ── AcquisitionCompletionSummary ──────────────────────────────────────────
struct AcquisitionCompletionSummary {
    std::string status        = "unknown";
    int         sample_count  = 0;
    double      span_seconds  = 0.0;
};

// ── _completion_summary_for ───────────────────────────────────────────────
// Mirrors session_index.py _completion_summary_for (non-bundle path).
AcquisitionCompletionSummary _completion_summary_for(const fs::path& csv_path) {
    fs::path acq_path = fs::path(csv_path).replace_extension(".acquisition.json");
    if (!fs::exists(acq_path)) return AcquisitionCompletionSummary{};
    try {
        auto provenance = read_acquisition_json(acq_path.string());
        const auto& completion = provenance.completion;
        std::string status = "unknown";
        if (completion.contains("status") && completion["status"].is_string()) {
            status = completion["status"].get<std::string>();
            // strip whitespace
            while (!status.empty() && (status.front() == ' ' || status.front() == '\t')) status.erase(status.begin());
            while (!status.empty() && (status.back() == ' ' || status.back() == '\t')) status.pop_back();
        }
        if (status != "finalized" && status != "open") status = "unknown";
        int sample_count = 0;
        if (completion.contains("sample_count")) {
            try {
                if (completion["sample_count"].is_number()) {
                    sample_count = std::max(0, completion["sample_count"].get<int>());
                } else if (completion["sample_count"].is_string()) {
                    sample_count = std::max(0, static_cast<int>(std::stod(completion["sample_count"].get<std::string>())));
                }
            } catch (...) {}
        }
        double span_seconds = 0.0;
        if (completion.contains("sample_span_seconds")) {
            try {
                double v = 0.0;
                if (completion["sample_span_seconds"].is_number())
                    v = completion["sample_span_seconds"].get<double>();
                else if (completion["sample_span_seconds"].is_string())
                    v = std::stod(completion["sample_span_seconds"].get<std::string>());
                span_seconds = std::round(v * 1e6) / 1e6;
            } catch (...) {}
        }
        return {status, sample_count, span_seconds};
    } catch (...) {
        return AcquisitionCompletionSummary{};
    }
}

// ── _completion_audit ─────────────────────────────────────────────────────
// Returns {audit, count_delta, span_delta}. Mirrors session_index.py L497.
std::tuple<std::string, int, double> _completion_audit(
    const AcquisitionCompletionSummary& completion,
    int actual_sample_count,
    double actual_span_seconds)
{
    if (completion.status == "open")
        return {"pending", 0, 0.0};
    if (completion.status != "finalized")
        return {"unknown", 0, 0.0};
    int count_delta = completion.sample_count - actual_sample_count;
    double span_delta = std::round((completion.span_seconds - actual_span_seconds) * 1e6) / 1e6;
    if (count_delta == 0 && std::abs(span_delta) <= 0.001)
        return {"pass", count_delta, span_delta};
    return {"fail", count_delta, span_delta};
}

// ── _recording_manifest_audit ─────────────────────────────────────────────
// Degraded: no manifest module ported.
std::pair<std::string, std::string> _recording_manifest_audit(const fs::path& csv_path) {
    fs::path manifest_path = fs::path(csv_path).replace_extension(".manifest.json");
    if (!fs::exists(manifest_path)) return {"missing", ""};
    return {"unknown", "manifest verification not available"};
}

// ── _row_for_csv ──────────────────────────────────────────────────────────
// Returns empty optional on skip.
std::optional<SessionIndexRow> _row_for_csv(const fs::path& path, const fs::path& root) {
    std::vector<ads1292::StreamSample> samples;
    try {
        samples = read_recording_csv(path.string());
    } catch (...) {
        return std::nullopt;
    }
    if (samples.empty()) return std::nullopt;

    constexpr double SAMPLE_RATE = 500.0;

    auto metadata = _metadata_for(path);
    auto metrics = ads1292::dsp::compute_quality_metrics(samples, SAMPLE_RATE, "Auto");
    auto [sidecar_status, missing_sidecars] = _sidecar_status(path);
    auto event_summary = _event_summary_for(path, SAMPLE_RATE);
    auto completion = _completion_summary_for(path);
    auto [audit, count_delta, span_delta] = _completion_audit(completion, metrics.sample_count, metrics.duration_seconds);
    auto [manifest_status, manifest_failures] = _recording_manifest_audit(path);

    std::string qlabel = ads1292::dsp::quality_label(metrics);
    std::string waveform_status = ads1292::index::status_for_quality(qlabel);
    std::string pkg_ready = ads1292::index::package_ready_status(waveform_status, sidecar_status);

    // Compute relative path in POSIX style
    std::string rel_path = fs::relative(path, root).generic_string();

    SessionIndexRow row;
    row.path = path.string();
    row.relative_path = rel_path;
    row.session_id = metadata.session_id;
    row.subject_id = metadata.subject_id;
    row.electrode = metadata.electrode;
    row.montage = metadata.montage;
    row.operator_ = metadata.operator_;
    row.sample_count = metrics.sample_count;
    row.duration_seconds = metrics.duration_seconds;
    row.completion_status = completion.status;
    row.recorded_sample_count = completion.sample_count;
    row.recorded_span_seconds = completion.span_seconds;
    row.completion_audit = audit;
    row.recorded_sample_count_delta = count_delta;
    row.recorded_span_delta_seconds = span_delta;
    row.ecg_source = metrics.ecg_source;
    row.contact_ok_percent = metrics.contact_ok_percent;
    row.r_peaks = metrics.r_peaks;
    row.hr_median_bpm = metrics.hr_median_bpm;
    row.qrs_clear = metrics.qrs_clear;
    row.quality_label = qlabel;
    row.status = waveform_status;
    row.sidecar_status = sidecar_status;
    row.missing_sidecars = missing_sidecars;
    row.event_count = event_summary.count;
    row.interval_event_count = event_summary.interval_count;
    row.total_annotated_seconds = event_summary.total_annotated_seconds;
    row.total_annotated_samples = event_summary.total_annotated_samples;
    row.event_labels = event_summary.labels;
    row.recording_manifest_status = manifest_status;
    row.recording_manifest_failures = manifest_failures;
    row.package_ready_status = pkg_ready;
    row.next_action = ads1292::index::next_action(pkg_ready);

    return row;
}

}  // anonymous namespace

// ── discover_recording_csvs ────────────────────────────────────────────────
std::vector<std::string> discover_recording_csvs(const std::string& root) {
    fs::path root_path(root);
    std::vector<fs::path> paths;
    for (const auto& entry : fs::recursive_directory_iterator(root_path)) {
        if (!entry.is_regular_file()) continue;
        if (entry.path().extension() != ".csv") continue;
        if (_looks_like_recording_csv(entry.path()))
            paths.push_back(entry.path());
    }
    std::sort(paths.begin(), paths.end());
    std::vector<std::string> result;
    result.reserve(paths.size());
    for (const auto& p : paths) result.push_back(p.string());
    return result;
}

// ── scan_recording_directory ──────────────────────────────────────────────
std::vector<SessionIndexRow> scan_recording_directory(const std::string& root) {
    fs::path root_path(root);
    auto csv_paths = discover_recording_csvs(root);
    std::vector<SessionIndexRow> rows;
    for (const auto& csv_str : csv_paths) {
        auto opt = _row_for_csv(fs::path(csv_str), root_path);
        if (opt) rows.push_back(std::move(*opt));
    }
    return rows;
}

// ── write_session_index_json ──────────────────────────────────────────────
void write_session_index_json(const std::string& path,
                              const std::vector<SessionIndexRow>& rows,
                              const SessionIndexSummary& summary)
{
    using ordered_json = nlohmann::ordered_json;
    ordered_json doc;

    ordered_json rows_arr = ordered_json::array();
    for (const auto& row : rows) {
        ordered_json r;
        r["path"] = row.path;
        r["relative_path"] = row.relative_path;
        r["session_id"] = row.session_id;
        r["subject_id"] = row.subject_id;
        r["electrode"] = row.electrode;
        r["montage"] = row.montage;
        r["operator"] = row.operator_;  // JSON key is "operator"
        r["sample_count"] = row.sample_count;
        r["duration_seconds"] = row.duration_seconds;
        r["completion_status"] = row.completion_status;
        r["recorded_sample_count"] = row.recorded_sample_count;
        r["recorded_span_seconds"] = row.recorded_span_seconds;
        r["completion_audit"] = row.completion_audit;
        r["recorded_sample_count_delta"] = row.recorded_sample_count_delta;
        r["recorded_span_delta_seconds"] = row.recorded_span_delta_seconds;
        r["ecg_source"] = row.ecg_source;
        r["contact_ok_percent"] = row.contact_ok_percent;
        r["r_peaks"] = row.r_peaks;
        r["hr_median_bpm"] = row.hr_median_bpm;
        r["qrs_clear"] = row.qrs_clear;
        r["quality_label"] = row.quality_label;
        r["status"] = row.status;
        r["sidecar_status"] = row.sidecar_status;
        r["missing_sidecars"] = row.missing_sidecars;
        r["event_count"] = row.event_count;
        r["interval_event_count"] = row.interval_event_count;
        r["total_annotated_seconds"] = row.total_annotated_seconds;
        r["total_annotated_samples"] = row.total_annotated_samples;
        r["event_labels"] = row.event_labels;
        r["recording_manifest_status"] = row.recording_manifest_status;
        r["recording_manifest_failures"] = row.recording_manifest_failures;
        r["package_ready_status"] = row.package_ready_status;
        r["next_action"] = row.next_action;
        rows_arr.push_back(r);
    }
    doc["rows"] = rows_arr;

    ordered_json sum;
    sum["recordings"] = summary.recordings;
    sum["usable_recordings"] = summary.usable_recordings;
    sum["package_ready"] = summary.package_ready;
    sum["incomplete_records"] = summary.incomplete_records;
    sum["needs_signal_review"] = summary.needs_signal_review;
    sum["finalized_recordings"] = summary.finalized_recordings;
    sum["open_recordings"] = summary.open_recordings;
    sum["unknown_completion_records"] = summary.unknown_completion_records;
    sum["completion_audit_pass"] = summary.completion_audit_pass;
    sum["completion_audit_fail"] = summary.completion_audit_fail;
    sum["completion_audit_pending"] = summary.completion_audit_pending;
    sum["completion_audit_unknown"] = summary.completion_audit_unknown;
    sum["recording_manifest_pass"] = summary.recording_manifest_pass;
    sum["recording_manifest_fail"] = summary.recording_manifest_fail;
    sum["recording_manifest_missing"] = summary.recording_manifest_missing;
    sum["recording_manifest_unknown"] = summary.recording_manifest_unknown;
    sum["annotated_recordings"] = summary.annotated_recordings;
    sum["event_annotations"] = summary.event_annotations;
    sum["interval_event_annotations"] = summary.interval_event_annotations;
    sum["total_annotated_seconds"] = summary.total_annotated_seconds;
    sum["total_annotated_samples"] = summary.total_annotated_samples;
    sum["action_package_record"] = summary.action_package_record;
    sum["action_complete_sidecars"] = summary.action_complete_sidecars;
    sum["action_review_signal"] = summary.action_review_signal;
    doc["summary"] = sum;

    std::ofstream out(path);
    if (!out.is_open()) throw std::runtime_error("Cannot open " + path + " for writing");
    out << doc.dump(2) << "\n";
}

}  // namespace io
}  // namespace ads1292
