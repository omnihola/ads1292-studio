// io/src/QualityGateIo.cpp
// Implements write_quality_gate_json + quality_gate_template.
// Port of quality_gate.py: write_quality_gate_json / quality_gate_template.
// No Qt; pure C++17 + nlohmann.
#include "ads1292/io/QualityGateIo.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {

ads1292::dsp::QualityGate quality_gate_template() {
    return ads1292::dsp::QualityGate{};  // all defaults match Python QualityGate()
}

void write_quality_gate_json(const std::string& path, const ads1292::dsp::QualityGate& gate) {
    // Normalize first, matching Python gate.normalized() call in write_quality_gate_json.
    const auto n = ads1292::dsp::normalized(gate);

    // Use ordered_json to preserve key order as specified.
    nlohmann::ordered_json j;
    j["min_duration_seconds"]   = n.min_duration_seconds;
    j["min_contact_ok_percent"] = n.min_contact_ok_percent;
    j["min_r_peaks"]            = n.min_r_peaks;
    j["min_hr_bpm"]             = n.min_hr_bpm;
    j["max_hr_bpm"]             = n.max_hr_bpm;
    j["require_qrs_clear"]      = n.require_qrs_clear;

    // Optional caps: JSON null when unset (std::nullopt), else the numeric value.
    // Matches Python asdict() of None fields → null.
    if (n.max_baseline_drift_counts.has_value())
        j["max_baseline_drift_counts"] = n.max_baseline_drift_counts.value();
    else
        j["max_baseline_drift_counts"] = nullptr;

    if (n.max_noise_rms_counts.has_value())
        j["max_noise_rms_counts"] = n.max_noise_rms_counts.value();
    else
        j["max_noise_rms_counts"] = nullptr;

    if (n.max_peak_to_peak_counts.has_value())
        j["max_peak_to_peak_counts"] = n.max_peak_to_peak_counts.value();
    else
        j["max_peak_to_peak_counts"] = nullptr;

    // Create parent directories if needed.
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }

    std::ofstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("QualityGateIo: cannot write file: " + path);
    }
    f << j.dump(2) << "\n";
}

}  // namespace io
}  // namespace ads1292
