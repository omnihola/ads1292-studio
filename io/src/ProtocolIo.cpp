// io/src/ProtocolIo.cpp
#include "ads1292/io/ProtocolIo.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {

namespace {

/// Build a ProtocolStep from an untrusted JSON object: ignore unknown keys,
/// default missing ones. Mirrors Python _step_from_mapping.
static ads1292::ProtocolStep step_from_json(const nlohmann::json& item) {
    ads1292::ProtocolStep s;
    // start_seconds
    if (item.contains("start_seconds") && item["start_seconds"].is_number())
        s.start_seconds = item["start_seconds"].get<double>();
    // duration_seconds
    if (item.contains("duration_seconds") && item["duration_seconds"].is_number())
        s.duration_seconds = item["duration_seconds"].get<double>();
    // label
    if (item.contains("label") && item["label"].is_string())
        s.label = item["label"].get<std::string>();
    // instruction
    if (item.contains("instruction") && item["instruction"].is_string())
        s.instruction = item["instruction"].get<std::string>();
    return s;
}

} // namespace

ads1292::TestProtocol read_protocol_json(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("ProtocolIo: cannot open file: " + path);
    }

    nlohmann::json j;
    f >> j;

    if (!j.is_object()) {
        throw std::runtime_error("ProtocolIo: root is not a JSON object in: " + path);
    }

    ads1292::TestProtocol p;

    if (j.contains("name") && j["name"].is_string())
        p.name = j["name"].get<std::string>();
    else if (j.contains("name"))
        p.name = "";

    if (j.contains("objective") && j["objective"].is_string())
        p.objective = j["objective"].get<std::string>();
    else if (j.contains("objective"))
        p.objective = "";

    if (j.contains("operator_instructions") && j["operator_instructions"].is_string())
        p.operator_instructions = j["operator_instructions"].get<std::string>();
    else if (j.contains("operator_instructions"))
        p.operator_instructions = "";

    if (j.contains("acceptance_notes") && j["acceptance_notes"].is_string())
        p.acceptance_notes = j["acceptance_notes"].get<std::string>();
    else if (j.contains("acceptance_notes"))
        p.acceptance_notes = "";

    // Parse steps array — forgiving: skip non-object elements
    if (j.contains("steps") && j["steps"].is_array()) {
        for (const auto& item : j["steps"]) {
            if (item.is_object()) {
                p.steps.push_back(step_from_json(item));
            }
        }
    }

    // Oracle read_protocol_json calls .normalized() on the result — match it.
    return p.normalized();
}

void write_protocol_json(const std::string& path, const ads1292::TestProtocol& p) {
    const auto n = p.normalized();

    // Use ordered_json to preserve field order in output.
    nlohmann::ordered_json j;
    j["name"]                  = n.name;
    j["objective"]             = n.objective;
    j["operator_instructions"] = n.operator_instructions;

    nlohmann::ordered_json steps = nlohmann::ordered_json::array();
    for (const auto& s : n.steps) {
        nlohmann::ordered_json step;
        step["start_seconds"]    = s.start_seconds;
        step["duration_seconds"] = s.duration_seconds;
        step["label"]            = s.label;
        step["instruction"]      = s.instruction;
        steps.push_back(step);
    }
    j["steps"]            = steps;
    j["acceptance_notes"] = n.acceptance_notes;

    // Create parent directories if needed.
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }

    std::ofstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("ProtocolIo: cannot write file: " + path);
    }
    f << j.dump(2) << "\n";
}

ads1292::TestProtocol protocol_template() {
    // Exact strings from Python protocol_template():
    ads1292::TestProtocol t;
    t.name                  = "MOTAC ECG validation";
    t.objective             = "Compare MOTAC gel electrode performance against a commercial Ag/AgCl control.";
    t.operator_instructions = "Use battery power, verify RA/LA/RL contact, and record protocol events.";
    t.acceptance_notes      = "Quality gate should pass; QRS should remain visible before, during, and after motion.";

    t.steps = {
        ads1292::ProtocolStep{
            0.0, 30.0,
            "baseline",
            "Subject seated and still; verify stable ECG and contact."
        },
        ads1292::ProtocolStep{
            30.0, 15.0,
            "motion",
            "Ask subject to move arm or torso gently to challenge adhesion."
        },
        ads1292::ProtocolStep{
            45.0, 30.0,
            "recovery",
            "Subject returns to still posture; confirm QRS recovery."
        },
    };

    return t;
}

}  // namespace io
}  // namespace ads1292
