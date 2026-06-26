// io/include/ads1292/io/QualityGateIo.h
#pragma once
#include <string>
#include "ads1292/dsp/QualityGate.h"

namespace ads1292 {
namespace io {

/// Returns the canonical quality_gate template (all defaults: QualityGate{}).
/// Matches Python quality_gate_template() = QualityGate().
ads1292::dsp::QualityGate quality_gate_template();

/// Write gate (after normalizing) as pretty-printed ordered JSON to path.
/// Keys in order: min_duration_seconds, min_contact_ok_percent, min_r_peaks,
/// min_hr_bpm, max_hr_bpm, require_qrs_clear, max_baseline_drift_counts,
/// max_noise_rms_counts, max_peak_to_peak_counts.
/// The 3 optional caps → JSON null when unset; else the numeric value.
/// Parent directories are created as needed.
void write_quality_gate_json(const std::string& path, const ads1292::dsp::QualityGate& gate);

}  // namespace io
}  // namespace ads1292
