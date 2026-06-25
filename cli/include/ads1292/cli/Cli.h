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

} // namespace ads1292::cli
