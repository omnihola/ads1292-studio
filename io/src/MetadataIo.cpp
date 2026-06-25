// io/src/MetadataIo.cpp
#include "ads1292/io/MetadataIo.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {

ads1292::SessionMetadata read_metadata_json(const std::string& path) {
  std::ifstream f(path);
  if (!f.is_open()) {
    throw std::runtime_error("MetadataIo: cannot open file: " + path);
  }

  nlohmann::json j;
  f >> j;

  if (!j.is_object()) {
    throw std::runtime_error("MetadataIo: root is not a JSON object in: " + path);
  }

  ads1292::SessionMetadata m;
  // For each known key, set the corresponding field; unknown keys are ignored.
  if (j.contains("session_id")       && j["session_id"].is_string())
    m.session_id       = j["session_id"].get<std::string>();
  if (j.contains("subject_id")       && j["subject_id"].is_string())
    m.subject_id       = j["subject_id"].get<std::string>();
  if (j.contains("electrode")        && j["electrode"].is_string())
    m.electrode        = j["electrode"].get<std::string>();
  if (j.contains("montage")          && j["montage"].is_string())
    m.montage          = j["montage"].get<std::string>();
  if (j.contains("operator")         && j["operator"].is_string())
    m.operator_        = j["operator"].get<std::string>();  // JSON key "operator" → field operator_
  if (j.contains("notes")            && j["notes"].is_string())
    m.notes            = j["notes"].get<std::string>();
  if (j.contains("acquisition_mode") && j["acquisition_mode"].is_string())
    m.acquisition_mode = j["acquisition_mode"].get<std::string>();

  return m.normalized();
}

void write_metadata_json(const std::string& path, const ads1292::SessionMetadata& m) {
  auto n = m.normalized();

  // Use ordered_json to preserve field order in output.
  nlohmann::ordered_json j;
  j["session_id"]       = n.session_id;
  j["subject_id"]       = n.subject_id;
  j["electrode"]        = n.electrode;
  j["montage"]          = n.montage;
  j["operator"]         = n.operator_;  // field operator_ → JSON key "operator"
  j["notes"]            = n.notes;
  j["acquisition_mode"] = n.acquisition_mode;

  // Create parent directories if needed.
  auto parent = std::filesystem::path(path).parent_path();
  if (!parent.empty()) {
    std::filesystem::create_directories(parent);
  }

  std::ofstream f(path);
  if (!f.is_open()) {
    throw std::runtime_error("MetadataIo: cannot write file: " + path);
  }
  f << j.dump(2) << "\n";
}

ads1292::SessionMetadata metadata_template() {
  ads1292::SessionMetadata m;
  m.session_id       = "YYYYMMDD-run-001";
  m.subject_id       = "anonymous";
  m.electrode        = "commercial Ag/AgCl control or MOTAC gel + Ag/AgCl";
  m.montage          = "RA/LA/RL torso";
  m.operator_        = "";
  m.notes            = "posture, movement condition, skin prep, gel formulation, electrode placement";
  m.acquisition_mode = "live_stream";
  return m;
}

}  // namespace io
}  // namespace ads1292
