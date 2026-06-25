// io/src/CalibrationIo.cpp
#include "ads1292/io/CalibrationIo.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {

ads1292::Calibration read_calibration_json(const std::string& path) {
  std::ifstream f(path);
  if (!f.is_open()) {
    throw std::runtime_error("CalibrationIo: cannot open file: " + path);
  }

  nlohmann::json j;
  f >> j;

  if (!j.is_object()) {
    throw std::runtime_error("CalibrationIo: root is not a JSON object in: " + path);
  }

  ads1292::Calibration c;
  // For each known key, set the corresponding field; unknown keys are ignored.
  if (j.contains("vref_mv") && j["vref_mv"].is_number())
    c.vref_mv = j["vref_mv"].get<double>();
  if (j.contains("pga_gain") && j["pga_gain"].is_number())
    c.pga_gain = j["pga_gain"].get<double>();
  if (j.contains("adc_bits") && j["adc_bits"].is_number_integer())
    c.adc_bits = j["adc_bits"].get<int>();
  if (j.contains("label") && j["label"].is_string())
    c.label = j["label"].get<std::string>();

  return c.normalized();
}

void write_calibration_json(const std::string& path, const ads1292::Calibration& c) {
  auto n = c.normalized();

  // Use ordered_json to preserve field order in output.
  nlohmann::ordered_json j;
  j["vref_mv"]  = n.vref_mv;
  j["pga_gain"] = n.pga_gain;
  j["adc_bits"] = n.adc_bits;
  j["label"]    = n.label;

  // Create parent directories if needed.
  auto parent = std::filesystem::path(path).parent_path();
  if (!parent.empty()) {
    std::filesystem::create_directories(parent);
  }

  std::ofstream f(path);
  if (!f.is_open()) {
    throw std::runtime_error("CalibrationIo: cannot write file: " + path);
  }
  f << j.dump(2) << "\n";
}

ads1292::Calibration calibration_template() {
  return ads1292::Calibration{};  // all defaults
}

}  // namespace io
}  // namespace ads1292
