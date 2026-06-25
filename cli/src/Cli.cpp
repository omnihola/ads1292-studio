// cli/src/Cli.cpp
// Qt-free implementation of the CLI subcommand library.

#include "ads1292/cli/Cli.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/H5Io.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/dsp/QualityGate.h"

#include <iomanip>
#include <stdexcept>

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

} // namespace ads1292::cli
