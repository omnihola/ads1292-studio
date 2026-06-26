// io/include/ads1292/io/QualityGateIo.h
#pragma once
#include <string>
#include <nlohmann/json.hpp>
#include "ads1292/dsp/QualityGate.h"

namespace ads1292 {
namespace io {

/// Return the ordered JSON object for @p gate (after normalizing).
/// Keys in order: min_duration_seconds, min_contact_ok_percent, min_r_peaks,
/// min_hr_bpm, max_hr_bpm, require_qrs_clear, max_baseline_drift_counts,
/// max_noise_rms_counts, max_peak_to_peak_counts.
/// The 3 optional caps → JSON null when unset; else the numeric value.
/// Byte-identical to the object written by write_quality_gate_json.
nlohmann::ordered_json quality_gate_to_json(const ads1292::dsp::QualityGate& gate);

/// Parse a JSON object @p j into a normalized QualityGate.
/// Uses defaults for missing/null fields; optional caps become std::nullopt when JSON null.
ads1292::dsp::QualityGate quality_gate_from_json(const nlohmann::json& j);

/// Read a quality-gate JSON file from @p path and return a normalized QualityGate.
/// Throws std::runtime_error if the file cannot be opened or the root is not a JSON object.
ads1292::dsp::QualityGate read_quality_gate_json(const std::string& path);

/// Returns the canonical quality_gate template (all defaults: QualityGate{}).
/// Matches Python quality_gate_template() = QualityGate().
ads1292::dsp::QualityGate quality_gate_template();

/// Write gate (after normalizing) as pretty-printed ordered JSON to path.
/// Parent directories are created as needed.
void write_quality_gate_json(const std::string& path, const ads1292::dsp::QualityGate& gate);

}  // namespace io
}  // namespace ads1292
