#pragma once
// io/include/ads1292/io/BatchScan.h
#include <string>
#include <vector>
#include "ads1292/index/BatchRow.h"

namespace ads1292 {
namespace io {

/// Aggregate a list of recording CSV paths into BatchRows.
///
/// For each path: read the CSV, read metadata from a sidecar JSON (<stem>.json)
/// if present, else construct a minimal SessionMetadata with session_id=stem.
/// Compute quality metrics and build a BatchRow.
/// Paths that cannot be read or produce empty recordings are silently skipped.
std::vector<ads1292::index::BatchRow> aggregate_recordings(
    const std::vector<std::string>& csv_paths);

}  // namespace io
}  // namespace ads1292
