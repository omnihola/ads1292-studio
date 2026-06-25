#pragma once
// io/include/ads1292/io/SessionIndexScan.h
#include <string>
#include <vector>
#include "ads1292/index/SessionIndexRow.h"

namespace ads1292 {
namespace io {

/// Return sorted recording CSV paths under root (recursive), excluding sidecar/index files.
std::vector<std::string> discover_recording_csvs(const std::string& root);

/// Scan all recording CSVs under root and build one SessionIndexRow per recording.
/// Rows for unreadable or empty CSVs are silently skipped.
std::vector<ads1292::index::SessionIndexRow> scan_recording_directory(const std::string& root);

/// Write {rows:[...], summary:{...}} as deterministic JSON (ordered_json, dump(2)+"\n") to path.
void write_session_index_json(const std::string& path,
                              const std::vector<ads1292::index::SessionIndexRow>& rows,
                              const ads1292::index::SessionIndexSummary& summary);

}  // namespace io
}  // namespace ads1292
