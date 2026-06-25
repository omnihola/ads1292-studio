// io/src/CsvIo.cpp
#include "ads1292/io/CsvIo.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace ads1292 {
namespace io {

const std::vector<std::string> CANONICAL_HEADER = {
    "timestamp", "sample_index", "ch1_counts", "ch2_counts",
    "board_heart_rate", "board_respiration_rate", "status_byte", "lead_off_bits"};

const std::vector<std::string> RAW_HEADER = {
    "timestamp", "sample_index", "ch1_raw24", "ch2_raw24", "ch1_uv", "ch2_uv",
    "status_byte", "lead_off_bits", "vref_mv", "pga_gain", "adc_bits",
    "raw_lsb_uv_per_count", "acquisition_mode"};

namespace {
std::string fmt(const char* spec, double v) {
  char buf[64];
  std::snprintf(buf, sizeof(buf), spec, v);
  return std::string(buf);
}

std::vector<std::string> split_csv_line(const std::string& line) {
  // The golden CSVs never quote (all fields are numbers or barewords without
  // commas), so a plain comma split is exact. Trailing '\r' is stripped.
  std::vector<std::string> out;
  std::string field;
  std::istringstream ss(line);
  while (std::getline(ss, field, ',')) {
    if (!field.empty() && field.back() == '\r') field.pop_back();
    out.push_back(field);
  }
  return out;
}

int header_index(const std::vector<std::string>& header, const std::string& name) {
  for (size_t i = 0; i < header.size(); ++i)
    if (header[i] == name) return static_cast<int>(i);
  return -1;
}

std::string cell(const std::vector<std::string>& row, int idx) {
  return (idx >= 0 && idx < static_cast<int>(row.size())) ? row[idx] : std::string();
}
}  // namespace

void write_recording_csv(const std::string& path, const std::vector<StreamSample>& samples) {
  std::ofstream out(path, std::ios::binary);
  if (!out) throw std::runtime_error("cannot open for write: " + path);
  // header + CRLF
  for (size_t i = 0; i < CANONICAL_HEADER.size(); ++i) {
    out << CANONICAL_HEADER[i];
    if (i + 1 < CANONICAL_HEADER.size()) out << ',';
  }
  out << "\r\n";
  int row_index = 0;
  for (const auto& s : samples) {
    int idx = s.sample_index.has_value() ? s.sample_index.value() : row_index;
    out << fmt("%.6f", s.timestamp) << ','
        << idx << ','
        << s.ch1 << ','
        << s.ch2 << ','
        << s.board_heart_rate << ','
        << s.board_respiration_rate << ','
        << s.status_byte << ','
        << s.lead_off_bits() << "\r\n";
    ++row_index;
  }
}

std::vector<StreamSample> read_recording_csv(const std::string& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("cannot open for read: " + path);
  std::string line;
  if (!std::getline(in, line)) return {};
  std::vector<std::string> header = split_csv_line(line);
  int ts = header_index(header, "timestamp");
  int idx = header_index(header, "sample_index");
  int ch1 = header_index(header, "ch1_counts");
  int ch2 = header_index(header, "ch2_counts");
  int hr = header_index(header, "board_heart_rate");
  int rr = header_index(header, "board_respiration_rate");
  int status = header_index(header, "status_byte");
  int lead = header_index(header, "lead_off_bits");

  std::vector<StreamSample> samples;
  int row_index = 0;
  while (std::getline(in, line)) {
    if (line.empty() || line == "\r") continue;
    std::vector<std::string> row = split_csv_line(line);
    StreamSample s;
    s.timestamp = cell(row, ts).empty() ? 0.0 : std::stod(cell(row, ts));
    s.ch1 = cell(row, ch1).empty() ? 0 : static_cast<int>(std::stod(cell(row, ch1)));
    s.ch2 = cell(row, ch2).empty() ? 0 : static_cast<int>(std::stod(cell(row, ch2)));
    s.board_heart_rate = cell(row, hr).empty() ? 0 : static_cast<int>(std::stod(cell(row, hr)));
    s.board_respiration_rate = cell(row, rr).empty() ? 0 : static_cast<int>(std::stod(cell(row, rr)));
    int status_byte = cell(row, status).empty() ? 0 : static_cast<int>(std::stod(cell(row, status)));
    std::string lead_cell = cell(row, lead);
    if (!lead_cell.empty()) {
      status_byte = (status_byte & ~0x0F) | (static_cast<int>(std::stod(lead_cell)) & 0x0F);
    }
    s.status_byte = status_byte;
    std::string idx_cell = cell(row, idx);
    s.sample_index = idx_cell.empty() ? row_index : static_cast<int>(std::stod(idx_cell));
    samples.push_back(s);
    ++row_index;
  }
  return samples;
}

// --- raw CSV functions: implemented in Task 4 ---
void write_raw_recording_csv(const std::string&, const std::vector<RawSample>&, const Calibration&) {
  throw std::runtime_error("write_raw_recording_csv not implemented");
}
std::vector<RawSample> read_raw_recording_csv(const std::string&) {
  throw std::runtime_error("read_raw_recording_csv not implemented");
}

}  // namespace io
}  // namespace ads1292
