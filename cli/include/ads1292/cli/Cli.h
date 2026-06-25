#pragma once
// cli/include/ads1292/cli/Cli.h
// Qt-free CLI library: subcommand entry points.
// Links ads1292_core + ads1292_io only (no Qt).

#include "ads1292/dsp/QualityGate.h"

#include <ostream>
#include <string>

namespace ads1292::cli {

/// Options for the `qc` subcommand.
struct QcOptions {
    std::string csv_path;
    std::string source        = "Auto";
    double      sample_rate_hz = 500.0;
    ads1292::dsp::QualityGate gate;
};

/// Run the quality-gate check on the recording at opt.csv_path.
///
/// Prints to `out` (in order):
///   quality_gate=<Pass|Fail>
///   ecg_source=<CH1|CH2>
///   quality=<quality label>
///   baseline_drift_counts=<:.1f>
///   noise_rms_counts=<:.1f>
///   peak_to_peak_counts=<:.1f>
///   failure=<msg>   (one line per failure, only if any)
///
/// Returns:
///   0  — gate passed
///   1  — read error or empty recording
///   2  — gate failed
int run_qc(std::ostream& out, const QcOptions& opt);

/// Options for the `report` subcommand.
struct ReportOptions {
    std::string csv_path;
    std::string source         = "Auto";
    double      sample_rate_hz = 500.0;
};

/// Print a full textual quality/HR summary for the recording at opt.csv_path.
///
/// Prints to `out` (in order):
///   ecg_source=, sample_count=, duration_seconds=<:.3f>,
///   contact_ok_percent=<:.2f>, r_peaks=, hr_median_bpm=<:.2f>,
///   hr_min_bpm=<:.2f>, hr_max_bpm=<:.2f>, qrs_clear=<true|false>,
///   p_tentative=<true|false>, t_tentative=<true|false>,
///   baseline_drift_counts=<:.1f>, noise_rms_counts=<:.1f>,
///   peak_to_peak_counts=<:.1f>, quality=<quality_label>
///
/// Returns 0 on success, 1 on read error or empty recording.
int run_report(std::ostream& out, const ReportOptions& opt);

/// Options for the `verify` subcommand.
struct VerifyOptions {
    std::string h5_path;
};

/// Verify the HDF5 recording at opt.h5_path.
///
/// Prints to `out`:
///   ok=<true|false>
///   checked=<N>
///   failure=<msg>   (one line per failure, if any)
///
/// Returns:
///   0  — verification ok
///   1  — exception / file unreadable
///   2  — verification failed
int run_verify(std::ostream& out, const VerifyOptions& opt);

/// Options for the `index` subcommand.
struct IndexOptions {
    std::string root;     ///< Directory to scan for recording CSVs.
    std::string out_dir;  ///< Output directory for index.json (created if absent).
};

/// Scan a recording directory and write a JSON session index.
///
/// Behaviour (mirrors cli.py cmd_index):
///   - If opt.root is not a directory, prints the diagnostic and proceeds with
///     an empty scan (returns 0).
///   - If no recording CSVs are found, prints the diagnostic and proceeds.
///   - Always writes <out_dir>/index.json and prints (in order):
///       index_json=<path>
///       rows=<N>
///       package_ready=<N>
///       incomplete_records=<N>
///       needs_signal_review=<N>
///       action_package_record=<N>
///       action_complete_sidecars=<N>
///       action_review_signal=<N>
///
/// Note: the Python csv=/html=/sidecar_plan_*/manifest_*/template lines are
/// intentionally NOT emitted — that rendering/repair tooling is deferred.
///
/// Returns 0 always.
int run_index(std::ostream& out, const IndexOptions& opt);

} // namespace ads1292::cli
