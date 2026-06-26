#pragma once
// io/include/ads1292/io/AcquisitionIo.h
// AcquisitionProvenance struct + JSON read/write for the acquisition sidecar.
// No Qt. AcquisitionProvenance lives here (in io) because it carries nlohmann::json blob fields,
// which would pull nlohmann into core if the struct lived there.

#include <map>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

namespace ads1292 {
namespace io {

// Schema / sentinel constants (mirrors acquisition.py)
static constexpr const char* ACQUISITION_SCHEMA    = "ads1292-acquisition-provenance-v1";
static constexpr const char* LIVE_CSV_SCHEMA       = "ads1292-studio-live-stream-v1";
static constexpr const char* RAW_CSV_SCHEMA        = "ads1292-studio-raw-adc-v1";
static constexpr const char* TIMESTAMP_REFERENCE   = "relative_seconds_from_recording_start";

/// One entry in the csv_columns array.
struct CsvColumn {
    std::string name;
    std::string unit;
    std::string description;
};

/// Provenance metadata written alongside every recording CSV.
/// Mirrors Python AcquisitionProvenance (acquisition.py).
struct AcquisitionProvenance {
    std::string schema            = ACQUISITION_SCHEMA;
    std::string csv_name          = "";
    std::string csv_schema        = LIVE_CSV_SCHEMA;
    std::string acquisition_mode  = "live_stream";
    std::string port              = "";
    double      sample_rate_hz    = 500.0;
    std::string started_at        = "";
    std::string timestamp_reference = TIMESTAMP_REFERENCE;
    std::map<std::string, std::string> channel_map;
    std::vector<CsvColumn>             csv_columns;
    nlohmann::json raw_adc         = nlohmann::json::object();
    nlohmann::json live_calibration = nlohmann::json::object();
    nlohmann::json completion       = nlohmann::json::object();

    /// Return a normalized copy.  Mirrors AcquisitionProvenance.normalized() in acquisition.py.
    AcquisitionProvenance normalized() const;
};

/// Return the canonical four-entry channel map (mirrors default_channel_map() in acquisition.py).
std::map<std::string, std::string> default_channel_map();

/// Return the default csv_columns for @p mode.
/// @p include_live_calibration adds the six live-calibration columns when true.
/// Mirrors default_csv_columns(acquisition_mode, include_live_calibration) in acquisition.py.
std::vector<CsvColumn> default_csv_columns(const std::string& mode, bool include_live_calibration = false);

/// Return the ordered JSON provenance object for @p a (after normalizing).
/// Keys in order: schema, csv_name, csv_schema, acquisition_mode, port, sample_rate_hz,
/// started_at, timestamp_reference, channel_map, csv_columns, raw_adc,
/// live_calibration, completion.
/// Byte-identical to the object written by write_acquisition_json.
nlohmann::ordered_json acquisition_to_json(const AcquisitionProvenance& a);

/// Parse @p path, fill an AcquisitionProvenance (unknown keys ignored, missing keys keep
/// defaults), call .normalized(), and return the result.
/// Throws std::runtime_error if the file cannot be opened or the root is not a JSON object.
AcquisitionProvenance read_acquisition_json(const std::string& path);

/// Write @p a (after normalizing) as pretty JSON to @p path.
/// Parent directories are created as needed.
void write_acquisition_json(const std::string& path, const AcquisitionProvenance& a);

}  // namespace io
}  // namespace ads1292
