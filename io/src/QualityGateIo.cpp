// io/src/QualityGateIo.cpp
// Implements quality_gate_from_json, read_quality_gate_json,
//   write_quality_gate_json + quality_gate_template.
// Port of quality_gate.py.
// No Qt; pure C++17 + nlohmann.
#include "ads1292/io/QualityGateIo.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {

ads1292::dsp::QualityGate quality_gate_from_json(const nlohmann::json& j) {
    // If not an object, return all-defaults (mirrors Python _mapping({}) → defaults).
    if (!j.is_object()) {
        return ads1292::dsp::normalized(ads1292::dsp::QualityGate{});
    }

    // Helpers mirroring Python _float_with_default and _optional_float.
    auto float_with_default = [&](const char* key, double def) -> double {
        if (!j.contains(key)) return def;
        const auto& v = j[key];
        if (v.is_null()) return def;
        if (v.is_number()) return v.get<double>();
        return def;
    };
    auto optional_float = [&](const char* key) -> std::optional<double> {
        if (!j.contains(key)) return std::nullopt;
        const auto& v = j[key];
        if (v.is_null()) return std::nullopt;
        if (v.is_number()) return v.get<double>();
        return std::nullopt;
    };

    ads1292::dsp::QualityGate g;
    g.min_duration_seconds    = float_with_default("min_duration_seconds",   8.0);
    g.min_contact_ok_percent  = float_with_default("min_contact_ok_percent", 95.0);
    g.min_r_peaks             = static_cast<int>(float_with_default("min_r_peaks", 5.0));
    g.min_hr_bpm              = float_with_default("min_hr_bpm",  35.0);
    g.max_hr_bpm              = float_with_default("max_hr_bpm", 180.0);
    // require_qrs_clear: bool, default true
    if (j.contains("require_qrs_clear") && j["require_qrs_clear"].is_boolean())
        g.require_qrs_clear = j["require_qrs_clear"].get<bool>();
    else
        g.require_qrs_clear = true;
    g.max_baseline_drift_counts = optional_float("max_baseline_drift_counts");
    g.max_noise_rms_counts      = optional_float("max_noise_rms_counts");
    g.max_peak_to_peak_counts   = optional_float("max_peak_to_peak_counts");
    return ads1292::dsp::normalized(g);
}

ads1292::dsp::QualityGate read_quality_gate_json(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("QualityGateIo: cannot open file: " + path);
    }
    nlohmann::json j;
    f >> j;
    if (!j.is_object()) {
        throw std::runtime_error("QualityGateIo: root is not a JSON object in: " + path);
    }
    return quality_gate_from_json(j);
}

ads1292::dsp::QualityGate quality_gate_template() {
    return ads1292::dsp::QualityGate{};  // all defaults match Python QualityGate()
}

nlohmann::ordered_json quality_gate_to_json(const ads1292::dsp::QualityGate& gate) {
    // Normalize first, matching Python gate.normalized() call in write_quality_gate_json.
    const auto n = ads1292::dsp::normalized(gate);

    nlohmann::ordered_json j;
    j["min_duration_seconds"]   = n.min_duration_seconds;
    j["min_contact_ok_percent"] = n.min_contact_ok_percent;
    j["min_r_peaks"]            = n.min_r_peaks;
    j["min_hr_bpm"]             = n.min_hr_bpm;
    j["max_hr_bpm"]             = n.max_hr_bpm;
    j["require_qrs_clear"]      = n.require_qrs_clear;

    // Optional caps: JSON null when unset (std::nullopt), else the numeric value.
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

    return j;
}

void write_quality_gate_json(const std::string& path, const ads1292::dsp::QualityGate& gate) {
    auto j = quality_gate_to_json(gate);

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
