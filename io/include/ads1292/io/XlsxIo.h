#pragma once
#include <string>
#include <vector>
#include "ads1292/model/EventMarker.h"

namespace ads1292::io {

/// Returns csv_path with extension replaced by ".xlsx".
std::string recording_xlsx_path(const std::string& csv_path);

/// Build a 2-tab (Events + Data) XLSX and write it next to the CSV.
/// Ports xlsx_io.py write_recording_xlsx exactly.
void write_recording_xlsx(const std::string& csv_path,
                          const std::vector<ads1292::EventMarker>& events,
                          double sample_rate_hz = 500.0);

} // namespace ads1292::io
