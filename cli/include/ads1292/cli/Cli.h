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

} // namespace ads1292::cli
