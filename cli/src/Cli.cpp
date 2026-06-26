// cli/src/Cli.cpp
// Qt-free implementation of the CLI subcommand library.

#include "ads1292/cli/Cli.h"
#include "ads1292/io/BatchScan.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/H5Io.h"
#include "ads1292/io/SessionIndexScan.h"
#include "ads1292/io/SidecarRepair.h"
#include "ads1292/index/BatchRow.h"
#include "ads1292/index/SessionIndexRow.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/dsp/QualityGate.h"

#include <filesystem>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace fs = std::filesystem;

namespace ads1292::cli {

int run_qc(std::ostream& out, const QcOptions& opt) {
    // 1. Read the recording
    std::vector<ads1292::StreamSample> samples;
    try {
        samples = ads1292::io::read_recording_csv(opt.csv_path);
    } catch (const std::exception& e) {
        out << "error=" << e.what() << "\n";
        return 1;
    }
    if (samples.empty()) {
        out << "error=recording is empty\n";
        return 1;
    }

    // 2. Compute quality metrics
    auto m = ads1292::dsp::compute_quality_metrics(samples, opt.sample_rate_hz, opt.source);

    // 3. Evaluate the gate
    auto r = ads1292::dsp::evaluate_quality_gate(m, opt.gate);

    // 4. Print output lines (exact format per Global Constraints)
    out << "quality_gate=" << r.label() << "\n";
    out << "ecg_source=" << m.ecg_source << "\n";
    out << "quality=" << ads1292::dsp::quality_label(m) << "\n";
    out << std::fixed << std::setprecision(1);
    out << "baseline_drift_counts=" << m.baseline_drift_counts << "\n";
    out << "noise_rms_counts=" << m.noise_rms_counts << "\n";
    out << "peak_to_peak_counts=" << m.peak_to_peak_counts << "\n";
    for (const auto& f : r.failures) {
        out << "failure=" << f << "\n";
    }

    // 5. Return exit code
    return r.passed ? 0 : 2;
}

int run_report(std::ostream& out, const ReportOptions& opt) {
    // 1. Read the recording
    std::vector<ads1292::StreamSample> samples;
    try {
        samples = ads1292::io::read_recording_csv(opt.csv_path);
    } catch (const std::exception& e) {
        out << "error=" << e.what() << "\n";
        return 1;
    }
    if (samples.empty()) {
        out << "error=recording is empty\n";
        return 1;
    }

    // 2. Compute quality metrics
    auto m = ads1292::dsp::compute_quality_metrics(samples, opt.sample_rate_hz, opt.source);

    // 3. Print key=value lines in the specified order
    out << "ecg_source=" << m.ecg_source << "\n";
    out << "sample_count=" << m.sample_count << "\n";
    out << std::fixed << std::setprecision(3)
        << "duration_seconds=" << m.duration_seconds << "\n";
    out << std::fixed << std::setprecision(2)
        << "contact_ok_percent=" << m.contact_ok_percent << "\n";
    out << "r_peaks=" << m.r_peaks << "\n";
    out << std::fixed << std::setprecision(2)
        << "hr_median_bpm=" << m.hr_median_bpm << "\n"
        << "hr_min_bpm=" << m.hr_min_bpm << "\n"
        << "hr_max_bpm=" << m.hr_max_bpm << "\n";
    out << "qrs_clear=" << (m.qrs_clear ? "true" : "false") << "\n";
    out << "p_tentative=" << (m.p_tentative ? "true" : "false") << "\n";
    out << "t_tentative=" << (m.t_tentative ? "true" : "false") << "\n";
    out << std::fixed << std::setprecision(1)
        << "baseline_drift_counts=" << m.baseline_drift_counts << "\n"
        << "noise_rms_counts=" << m.noise_rms_counts << "\n"
        << "peak_to_peak_counts=" << m.peak_to_peak_counts << "\n";
    out << "quality=" << ads1292::dsp::quality_label(m) << "\n";

    return 0;
}

int run_verify(std::ostream& out, const VerifyOptions& opt) {
    ads1292::io::H5Verification v;
    try {
        v = ads1292::io::verify_recording_h5(opt.h5_path);
    } catch (const std::exception& e) {
        out << "error=" << e.what() << "\n";
        return 1;
    }

    out << "ok=" << (v.ok ? "true" : "false") << "\n";
    out << "checked=" << v.checked << "\n";
    for (const auto& f : v.failures) {
        out << "failure=" << f << "\n";
    }

    return v.ok ? 0 : 2;
}

int run_index(std::ostream& out, const IndexOptions& opt) {
    // --- diagnostics (non-fatal: proceed with empty scan if triggered) ---
    if (!fs::is_directory(opt.root)) {
        out << "index expects a directory; '" << opt.root << "' is not a directory\n";
        // fall through: scan produces empty rows
    } else if (ads1292::io::discover_recording_csvs(opt.root).empty()) {
        out << "no recording CSVs found under " << opt.root << "\n";
    }

    // --- scan ---
    std::vector<ads1292::index::SessionIndexRow> rows;
    try {
        rows = ads1292::io::scan_recording_directory(opt.root);
    } catch (...) {
        rows.clear(); // treat any exception as empty
    }

    // --- summarize ---
    auto summary = ads1292::index::summarize_rows(rows);

    // --- write JSON index ---
    fs::create_directories(opt.out_dir);
    auto json_path = (fs::path(opt.out_dir) / "index.json").string();
    ads1292::io::write_session_index_json(json_path, rows, summary);

    // --- print deterministic counter lines ---
    // Note: Python csv=/html=/sidecar_plan_*/manifest_*/template lines are
    // intentionally omitted — that rendering/repair tooling is deferred.
    out << "index_json=" << json_path << "\n";
    out << "rows=" << rows.size() << "\n";
    out << "package_ready=" << summary.package_ready << "\n";
    out << "incomplete_records=" << summary.incomplete_records << "\n";
    out << "needs_signal_review=" << summary.needs_signal_review << "\n";
    out << "action_package_record=" << summary.action_package_record << "\n";
    out << "action_complete_sidecars=" << summary.action_complete_sidecars << "\n";
    out << "action_review_signal=" << summary.action_review_signal << "\n";

    // --- write sidecar template bundle + apply script ---
    auto tdir   = (fs::path(opt.out_dir) / "sidecar-templates").string();
    auto plan   = ads1292::io::build_sidecar_completion_plan(rows, tdir);
    ads1292::io::write_sidecar_template_bundle(tdir, rows);
    auto script = (fs::path(opt.out_dir) / "apply-sidecars.sh").string();
    ads1292::io::write_sidecar_apply_script(script, plan);
    out << "sidecar_plan_rows=" << plan.size() << "\n";
    out << "sidecar_apply_script=" << script << "\n";

    return 0;
}

int run_batch(std::ostream& out, const BatchOptions& opt) {
    // --- resolve inputs (mirrors _resolve_batch_inputs in cli.py) ---
    std::vector<std::string> paths;
    for (const auto& input : opt.inputs) {
        if (fs::is_directory(input)) {
            auto csvs = ads1292::io::discover_recording_csvs(input);
            paths.insert(paths.end(), csvs.begin(), csvs.end());
        } else {
            paths.push_back(input);
        }
    }

    if (paths.empty()) {
        out << "no recording CSVs found in the given path(s)\n";
    }

    // --- aggregate + group ---
    auto rows   = ads1292::io::aggregate_recordings(paths);
    auto groups = ads1292::index::group_recordings_by_electrode(rows);

    // --- print deterministic counter lines ---
    // Note: Python csv=/group_csv=/html=/png= lines are intentionally omitted —
    // rendering/chart tooling is deferred.
    out << "rows=" << rows.size() << "\n";
    out << "groups=" << groups.size() << "\n";

    for (const auto& g : groups) {
        std::ostringstream line;
        line << std::fixed << std::setprecision(2);
        line << "group=" << g.electrode
             << "\trecordings=" << g.recordings
             << "\tusable_percent=" << g.usable_percent
             << "\tmean_hr_median_bpm=" << g.mean_hr_median_bpm
             << "\n";
        out << line.str();
    }

    return 0;
}

} // namespace ads1292::cli
