// io/src/ProcessingIo.cpp
#include "ads1292/io/ProcessingIo.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {

namespace {

/// Trim ASCII whitespace from both ends; return fallback if result is empty.
static std::string clean(const std::string& value, const std::string& fallback) {
    const auto is_ws = [](unsigned char c) {
        return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
    };
    auto begin = value.begin();
    while (begin != value.end() && is_ws(static_cast<unsigned char>(*begin)))
        ++begin;
    auto end = value.end();
    while (end != begin && is_ws(static_cast<unsigned char>(*(end - 1))))
        --end;
    const std::string trimmed(begin, end);
    return trimmed.empty() ? fallback : trimmed;
}

} // namespace

ads1292::RecordingProcessingSettings read_processing_json(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("ProcessingIo: cannot open file: " + path);
    }

    nlohmann::json j;
    f >> j;

    if (!j.is_object()) {
        throw std::runtime_error("ProcessingIo: root is not a JSON object in: " + path);
    }

    ads1292::RecordingProcessingSettings p;

    if (j.contains("schema") && j["schema"].is_string())
        p.schema = j["schema"].get<std::string>();

    // Nested display sub-object → EcgDisplaySettings fields
    if (j.contains("display") && j["display"].is_object()) {
        const auto& d = j["display"];
        if (d.contains("time_window_seconds") && d["time_window_seconds"].is_number())
            p.display.time_window_seconds = d["time_window_seconds"].get<double>();
        if (d.contains("gain") && d["gain"].is_number())
            p.display.gain = d["gain"].get<double>();
        if (d.contains("sweep_speed_mm_s") && d["sweep_speed_mm_s"].is_number())
            p.display.sweep_speed_mm_s = d["sweep_speed_mm_s"].get<int>();
    }

    // Nested software_filters sub-object → SoftwareFilterSettings fields
    if (j.contains("software_filters") && j["software_filters"].is_object()) {
        const auto& sf = j["software_filters"];
        if (sf.contains("highpass_enabled") && sf["highpass_enabled"].is_boolean())
            p.software_filters.highpass_enabled = sf["highpass_enabled"].get<bool>();
        if (sf.contains("notch_enabled") && sf["notch_enabled"].is_boolean())
            p.software_filters.notch_enabled = sf["notch_enabled"].get<bool>();
        if (sf.contains("lowpass_enabled") && sf["lowpass_enabled"].is_boolean())
            p.software_filters.lowpass_enabled = sf["lowpass_enabled"].get<bool>();
        if (sf.contains("bandpass_enabled") && sf["bandpass_enabled"].is_boolean())
            p.software_filters.bandpass_enabled = sf["bandpass_enabled"].get<bool>();
        if (sf.contains("highpass_hz") && sf["highpass_hz"].is_number())
            p.software_filters.highpass_hz = sf["highpass_hz"].get<double>();
        if (sf.contains("notch_hz") && sf["notch_hz"].is_number())
            p.software_filters.notch_hz = sf["notch_hz"].get<double>();
        if (sf.contains("lowpass_hz") && sf["lowpass_hz"].is_number())
            p.software_filters.lowpass_hz = sf["lowpass_hz"].get<double>();
    }

    if (j.contains("sample_rate_hz") && j["sample_rate_hz"].is_number())
        p.sample_rate_hz = j["sample_rate_hz"].get<double>();
    if (j.contains("ecg_inverted") && j["ecg_inverted"].is_boolean())
        p.ecg_inverted = j["ecg_inverted"].get<bool>();
    if (j.contains("smoothing_window") && j["smoothing_window"].is_number())
        p.smoothing_window = j["smoothing_window"].get<int>();
    if (j.contains("processing_notes") && j["processing_notes"].is_string())
        p.processing_notes = j["processing_notes"].get<std::string>();

    return p.normalized();
}

nlohmann::ordered_json processing_to_json(const ads1292::RecordingProcessingSettings& p) {
    const auto n = p.normalized();

    nlohmann::ordered_json j;
    j["schema"] = n.schema;

    // Nested display object: time_window_seconds, gain, sweep_speed_mm_s
    nlohmann::ordered_json display;
    display["time_window_seconds"] = n.display.time_window_seconds;
    display["gain"]                = n.display.gain;
    display["sweep_speed_mm_s"]    = n.display.sweep_speed_mm_s;
    j["display"] = display;

    // Nested software_filters object
    nlohmann::ordered_json sf;
    sf["highpass_enabled"]  = n.software_filters.highpass_enabled;
    sf["notch_enabled"]     = n.software_filters.notch_enabled;
    sf["lowpass_enabled"]   = n.software_filters.lowpass_enabled;
    sf["bandpass_enabled"]  = n.software_filters.bandpass_enabled;
    sf["highpass_hz"]       = n.software_filters.highpass_hz;
    sf["notch_hz"]          = n.software_filters.notch_hz;
    sf["lowpass_hz"]        = n.software_filters.lowpass_hz;
    j["software_filters"] = sf;

    j["sample_rate_hz"]   = n.sample_rate_hz;
    j["ecg_inverted"]     = n.ecg_inverted;
    j["smoothing_window"] = n.smoothing_window;
    j["processing_notes"] = n.processing_notes;
    return j;
}

void write_processing_json(const std::string& path, const ads1292::RecordingProcessingSettings& p) {
    auto j = processing_to_json(p);

    // Create parent directories if needed.
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }

    std::ofstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("ProcessingIo: cannot write file: " + path);
    }
    f << j.dump(2) << "\n";
}

ads1292::RecordingProcessingSettings build_processing_settings() {
    // Matches Python build_processing_settings() with no arguments:
    // EcgDisplaySettings().normalized() → display defaults (8.0, 1.0, 25)
    // SoftwareFilterSettings()          → all filters false / 0.5 / 60.0 / 40.0
    // sample_rate_hz=500.0, ecg_inverted=false, smoothing_window=11
    return ads1292::RecordingProcessingSettings{}.normalized();
}

}  // namespace io
}  // namespace ads1292
