// io/src/AcquisitionIo.cpp
// Implements AcquisitionProvenance + JSON helpers.
// Mirrors acquisition.py + csv_io.py (CANONICAL_HEADER / RAW_HEADER / LIVE_CALIBRATION_COLUMNS).
// No Qt.

#include "ads1292/io/AcquisitionIo.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <cctype>

namespace ads1292 {
namespace io {

// ---------------------------------------------------------------------------
// File-local constants — mirrors csv_io.py
// ---------------------------------------------------------------------------
namespace {

const std::vector<std::string> CANONICAL_HEADER = {
    "timestamp",
    "sample_index",
    "ch1_counts",
    "ch2_counts",
    "board_heart_rate",
    "board_respiration_rate",
    "status_byte",
    "lead_off_bits",
};

const std::vector<std::string> LIVE_CALIBRATION_COLUMNS = {
    "live_scale_uv_per_count",
    "live_scale_std_uv_per_count",
    "live_scale_cv_percent",
    "live_scale_runs",
    "live_test_signal_pp_uv",
    "live_scale_type",
};

const std::vector<std::string> RAW_HEADER = {
    "timestamp",
    "sample_index",
    "ch1_raw24",
    "ch2_raw24",
    "ch1_uv",
    "ch2_uv",
    "status_byte",
    "lead_off_bits",
    "vref_mv",
    "pga_gain",
    "adc_bits",
    "raw_lsb_uv_per_count",
    "acquisition_mode",
};

// ---------------------------------------------------------------------------
// Per-column metadata tables — mirrors acquisition.py
// ---------------------------------------------------------------------------
const std::map<std::string, std::string> CSV_COLUMN_UNITS = {
    {"timestamp",                  "s"},
    {"ch1_counts",                 "live_stream_count"},
    {"ch2_counts",                 "live_stream_count"},
    {"board_heart_rate",           "bpm"},
    {"board_respiration_rate",     "breaths/min"},
    {"status_byte",                "bitfield"},
    {"lead_off_bits",              "bitfield"},
    {"live_scale_uv_per_count",    "uV/count"},
    {"live_scale_std_uv_per_count","uV/count"},
    {"live_scale_cv_percent",      "%"},
    {"live_scale_runs",            "count"},
    {"live_test_signal_pp_uv",     "uV"},
    {"live_scale_type",            "text"},
    {"sample_index",               "sample"},
    {"ch1_raw24",                  "ADC count"},
    {"ch2_raw24",                  "ADC count"},
    {"ch1_uv",                     "uV"},
    {"ch2_uv",                     "uV"},
    {"vref_mv",                    "mV"},
    {"pga_gain",                   "V/V"},
    {"adc_bits",                   "bit"},
    {"raw_lsb_uv_per_count",       "uV/count"},
    {"acquisition_mode",           "text"},
};

const std::map<std::string, std::string> CSV_COLUMN_DESCRIPTIONS = {
    {"timestamp",                  "Relative seconds from recording start."},
    {"ch1_counts",                 "CH1 respiration/raw impedance"},
    {"ch2_counts",                 "CH2 ECG Lead I (LA-RA)"},
    {"board_heart_rate",           "Heart rate reported by ADS1x9x ECG-FE firmware."},
    {"board_respiration_rate",     "Respiration rate reported by ADS1x9x ECG-FE firmware."},
    {"status_byte",                "ADS1x9x status byte from the USB stream."},
    {"lead_off_bits",              "Low-nibble lead-off/contact status bits."},
    {"live_scale_uv_per_count",    "Live-stream calibration mean scale."},
    {"live_scale_std_uv_per_count","Live-stream calibration scale standard deviation."},
    {"live_scale_cv_percent",      "Live-stream calibration coefficient of variation."},
    {"live_scale_runs",            "Number of live calibration runs."},
    {"live_test_signal_pp_uv",     "Internal test signal peak-to-peak amplitude used for live calibration."},
    {"live_scale_type",            "Live-stream scale provenance label."},
    {"sample_index",               "Zero-based sample index."},
    {"ch1_raw24",                  "CH1 signed 24-bit raw ADS1292 ADC code."},
    {"ch2_raw24",                  "CH2 signed 24-bit raw ADS1292 ADC code."},
    {"ch1_uv",                     "CH1 raw ADC value converted to microvolts using raw_lsb_uv_per_count."},
    {"ch2_uv",                     "CH2 raw ADC value converted to microvolts using raw_lsb_uv_per_count."},
    {"vref_mv",                    "Reference voltage used for raw ADC conversion."},
    {"pga_gain",                   "PGA gain used for raw ADC conversion."},
    {"adc_bits",                   "ADC resolution used for raw ADC conversion."},
    {"raw_lsb_uv_per_count",       "Raw ADC least-significant-bit scale."},
    {"acquisition_mode",           "CSV acquisition mode label."},
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Trim ASCII whitespace from both ends of @p s.
static std::string trim(const std::string& s) {
    const auto is_ws = [](unsigned char c) {
        return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
    };
    auto b = s.begin();
    while (b != s.end() && is_ws(static_cast<unsigned char>(*b))) ++b;
    auto e = s.end();
    while (e != b && is_ws(static_cast<unsigned char>(*(e - 1)))) --e;
    return std::string(b, e);
}

/// Trim @p value; return @p fallback if result is empty.
static std::string clean(const std::string& value, const std::string& fallback) {
    const std::string t = trim(value);
    return t.empty() ? fallback : t;
}

/// Mirrors acquisition.py _normalized_mode().
static std::string normalized_mode(const std::string& value) {
    std::string text = trim(value);
    // to lower
    std::transform(text.begin(), text.end(), text.begin(),
                   [](unsigned char c){ return static_cast<char>(std::tolower(c)); });
    // strip "acquisitionmode." prefix
    const std::string prefix = "acquisitionmode.";
    if (text.size() > prefix.size() && text.substr(0, prefix.size()) == prefix) {
        text = text.substr(prefix.size());
    }
    if (text.rfind("raw", 0) == 0) {
        return "raw_adc_24bit";
    }
    return "live_stream";
}

/// Mirrors acquisition.py _clean_string_map().
static std::map<std::string, std::string> clean_string_map(const std::map<std::string, std::string>& values) {
    std::map<std::string, std::string> result;
    for (const auto& kv : values) {
        const std::string k = trim(kv.first);
        const std::string v = trim(kv.second);
        if (!k.empty() && !v.empty()) {
            result[k] = v;
        }
    }
    return result;
}

/// Mirrors acquisition.py _clean_csv_columns().
static std::vector<CsvColumn> clean_csv_columns(const std::vector<CsvColumn>& columns) {
    std::vector<CsvColumn> result;
    for (const auto& col : columns) {
        const std::string name = trim(col.name);
        if (name.empty()) continue;
        result.push_back({name, trim(col.unit), trim(col.description)});
    }
    return result;
}

/// Mirrors acquisition.py _clean_timestamp_reference().
static std::string clean_timestamp_reference(const std::string& value) {
    const std::string t = trim(value);
    return t.empty() ? TIMESTAMP_REFERENCE : t;
}

/// Build the open-completion sentinel dict (mirrors _open_completion()).
static nlohmann::json open_completion() {
    nlohmann::ordered_json c;
    c["status"]                  = "open";
    c["ended_at"]                = "";
    c["finalized_at"]            = "";
    c["sample_count"]            = 0;
    c["first_timestamp_seconds"] = 0.0;
    c["last_timestamp_seconds"]  = 0.0;
    c["sample_span_seconds"]     = 0.0;
    return c;
}

/// Mirrors acquisition.py _finalized_completion().
static nlohmann::json finalized_completion(
    const std::string& ended_at,
    const std::string& finalized_at,
    int sample_count,
    double first_timestamp_seconds,
    double last_timestamp_seconds)
{
    const double first = std::max(0.0, first_timestamp_seconds);
    const double last  = std::max(first, last_timestamp_seconds);
    // Round to 6 decimal places
    auto round6 = [](double v) -> double {
        return std::round(v * 1e6) / 1e6;
    };
    nlohmann::ordered_json c;
    c["status"]                  = "finalized";
    c["ended_at"]                = trim(ended_at);
    c["finalized_at"]            = trim(finalized_at);
    c["sample_count"]            = std::max(0, sample_count);
    c["first_timestamp_seconds"] = round6(first);
    c["last_timestamp_seconds"]  = round6(last);
    c["sample_span_seconds"]     = round6(last - first);
    return c;
}

/// Mirrors acquisition.py _clean_completion().
static nlohmann::json clean_completion(const nlohmann::json& value) {
    if (!value.is_object()) {
        return open_completion();
    }
    std::string status = "open";
    if (value.contains("status") && value["status"].is_string()) {
        status = trim(value["status"].get<std::string>());
        // to lower
        std::transform(status.begin(), status.end(), status.begin(),
                       [](unsigned char c){ return static_cast<char>(std::tolower(c)); });
    }
    if (status != "finalized") {
        return open_completion();
    }
    // Extract finalized fields
    std::string ended_at;
    std::string finalized_at;
    int sample_count = 0;
    double first_ts = 0.0;
    double last_ts  = 0.0;

    auto safe_str = [&](const char* key) -> std::string {
        if (value.contains(key) && value[key].is_string()) return value[key].get<std::string>();
        return "";
    };
    auto safe_int = [&](const char* key) -> int {
        if (!value.contains(key)) return 0;
        const auto& v = value[key];
        if (v.is_number_integer()) return v.get<int>();
        if (v.is_number_float())   return static_cast<int>(v.get<double>());
        if (v.is_string()) {
            try { return static_cast<int>(std::stod(v.get<std::string>())); } catch (...) {}
        }
        return 0;
    };
    auto safe_double = [&](const char* key) -> double {
        if (!value.contains(key)) return 0.0;
        const auto& v = value[key];
        if (v.is_number()) return v.get<double>();
        if (v.is_string()) {
            try { return std::stod(v.get<std::string>()); } catch (...) {}
        }
        return 0.0;
    };

    ended_at    = safe_str("ended_at");
    finalized_at = safe_str("finalized_at");
    sample_count = safe_int("sample_count");
    first_ts    = safe_double("first_timestamp_seconds");
    last_ts     = safe_double("last_timestamp_seconds");

    return finalized_completion(ended_at, finalized_at, sample_count, first_ts, last_ts);
}

/// One CsvColumn entry from the lookup tables (mirrors _csv_column_entry() in acquisition.py).
static CsvColumn csv_column_entry(const std::string& name) {
    CsvColumn col;
    col.name = name;
    auto uit = CSV_COLUMN_UNITS.find(name);
    col.unit = (uit != CSV_COLUMN_UNITS.end()) ? uit->second : "";
    auto dit = CSV_COLUMN_DESCRIPTIONS.find(name);
    col.description = (dit != CSV_COLUMN_DESCRIPTIONS.end()) ? dit->second : name;
    return col;
}

}  // namespace (anonymous)

// ---------------------------------------------------------------------------
// Public interface
// ---------------------------------------------------------------------------

std::map<std::string, std::string> default_channel_map() {
    return {
        {"ch1_counts",    "CH1 respiration/raw impedance"},
        {"ch2_counts",    "CH2 ECG Lead I (LA-RA)"},
        {"status_byte",   "ADS1x9x status byte"},
        {"lead_off_bits", "lead-off/contact status low nibble"},
    };
}

std::vector<CsvColumn> default_csv_columns(const std::string& mode, bool include_live_calibration) {
    const std::string m = normalized_mode(mode);
    const std::vector<std::string>* names =
        (m == "raw_adc_24bit") ? &RAW_HEADER : &CANONICAL_HEADER;

    std::vector<CsvColumn> result;
    result.reserve(names->size());
    for (const auto& n : *names) {
        result.push_back(csv_column_entry(n));
    }
    if (m != "raw_adc_24bit" && include_live_calibration) {
        for (const auto& n : LIVE_CALIBRATION_COLUMNS) {
            result.push_back(csv_column_entry(n));
        }
    }
    return result;
}

// ---------------------------------------------------------------------------
// AcquisitionProvenance::normalized()
// Mirrors AcquisitionProvenance.normalized() in acquisition.py exactly.
// ---------------------------------------------------------------------------
AcquisitionProvenance AcquisitionProvenance::normalized() const {
    const std::string mode = normalized_mode(acquisition_mode);
    const std::string csv_sch =
        (mode == "raw_adc_24bit") ? RAW_CSV_SCHEMA : LIVE_CSV_SCHEMA;

    // live_calibration passes through as a copy
    nlohmann::json live_cal = live_calibration;

    // channel_map
    std::map<std::string, std::string> ch_map = clean_string_map(channel_map);
    if (ch_map.empty()) {
        ch_map = default_channel_map();
    }

    // csv_columns
    std::vector<CsvColumn> cols = clean_csv_columns(csv_columns);
    if (cols.empty()) {
        cols = default_csv_columns(mode, !live_cal.empty());
    }

    AcquisitionProvenance n;
    n.schema              = clean(schema, ACQUISITION_SCHEMA);
    n.csv_name            = trim(csv_name);
    n.csv_schema          = csv_sch;
    n.acquisition_mode    = mode;
    n.port                = trim(port);
    n.sample_rate_hz      = (sample_rate_hz > 0.0) ? sample_rate_hz : 500.0;
    n.started_at          = trim(started_at);
    n.timestamp_reference = clean_timestamp_reference(timestamp_reference);
    n.channel_map         = ch_map;
    n.csv_columns         = cols;
    n.raw_adc             = raw_adc;       // pass through
    n.live_calibration    = live_cal;
    n.completion          = clean_completion(completion);
    return n;
}

// ---------------------------------------------------------------------------
// read_acquisition_json
// Mirrors read_acquisition_json() in acquisition.py — reads, maps allowed
// fields, returns .normalized().
// ---------------------------------------------------------------------------
AcquisitionProvenance read_acquisition_json(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("AcquisitionIo: cannot open file: " + path);
    }
    nlohmann::json j;
    f >> j;
    if (!j.is_object()) {
        throw std::runtime_error("AcquisitionIo: root is not a JSON object in: " + path);
    }

    AcquisitionProvenance a;

    if (j.contains("schema") && j["schema"].is_string())
        a.schema = j["schema"].get<std::string>();
    if (j.contains("csv_name") && j["csv_name"].is_string())
        a.csv_name = j["csv_name"].get<std::string>();
    if (j.contains("csv_schema") && j["csv_schema"].is_string())
        a.csv_schema = j["csv_schema"].get<std::string>();
    if (j.contains("acquisition_mode") && j["acquisition_mode"].is_string())
        a.acquisition_mode = j["acquisition_mode"].get<std::string>();
    if (j.contains("port") && j["port"].is_string())
        a.port = j["port"].get<std::string>();
    if (j.contains("sample_rate_hz") && j["sample_rate_hz"].is_number())
        a.sample_rate_hz = j["sample_rate_hz"].get<double>();
    if (j.contains("started_at") && j["started_at"].is_string())
        a.started_at = j["started_at"].get<std::string>();
    if (j.contains("timestamp_reference") && j["timestamp_reference"].is_string())
        a.timestamp_reference = j["timestamp_reference"].get<std::string>();

    // channel_map: JSON object → map<string,string>
    if (j.contains("channel_map") && j["channel_map"].is_object()) {
        for (auto& [k, v] : j["channel_map"].items()) {
            if (v.is_string()) {
                a.channel_map[k] = v.get<std::string>();
            }
        }
    }

    // csv_columns: JSON array of {name, unit, description}
    if (j.contains("csv_columns") && j["csv_columns"].is_array()) {
        for (const auto& item : j["csv_columns"]) {
            if (!item.is_object()) continue;
            CsvColumn col;
            if (item.contains("name") && item["name"].is_string())
                col.name = item["name"].get<std::string>();
            if (item.contains("unit") && item["unit"].is_string())
                col.unit = item["unit"].get<std::string>();
            if (item.contains("description") && item["description"].is_string())
                col.description = item["description"].get<std::string>();
            a.csv_columns.push_back(col);
        }
    }

    // raw_adc, live_calibration, completion: arbitrary JSON blobs
    if (j.contains("raw_adc"))
        a.raw_adc = j["raw_adc"];
    if (j.contains("live_calibration"))
        a.live_calibration = j["live_calibration"];
    if (j.contains("completion"))
        a.completion = j["completion"];

    return a.normalized();
}

// ---------------------------------------------------------------------------
// acquisition_to_json
// Serialises a.normalized() with keys in field order (mirrors asdict order
// from acquisition.py).
// ---------------------------------------------------------------------------
nlohmann::ordered_json acquisition_to_json(const AcquisitionProvenance& a) {
    const AcquisitionProvenance n = a.normalized();

    nlohmann::ordered_json j;
    j["schema"]              = n.schema;
    j["csv_name"]            = n.csv_name;
    j["csv_schema"]          = n.csv_schema;
    j["acquisition_mode"]    = n.acquisition_mode;
    j["port"]                = n.port;
    j["sample_rate_hz"]      = n.sample_rate_hz;
    j["started_at"]          = n.started_at;
    j["timestamp_reference"] = n.timestamp_reference;

    // channel_map: object (std::map iterates in key-sorted order)
    nlohmann::ordered_json ch_map = nlohmann::ordered_json::object();
    for (const auto& kv : n.channel_map) {
        ch_map[kv.first] = kv.second;
    }
    j["channel_map"] = ch_map;

    // csv_columns: array of {name, unit, description}
    nlohmann::ordered_json cols = nlohmann::ordered_json::array();
    for (const auto& col : n.csv_columns) {
        nlohmann::ordered_json entry;
        entry["name"]        = col.name;
        entry["unit"]        = col.unit;
        entry["description"] = col.description;
        cols.push_back(entry);
    }
    j["csv_columns"]      = cols;
    j["raw_adc"]          = n.raw_adc;
    j["live_calibration"] = n.live_calibration;
    j["completion"]       = n.completion;
    return j;
}

// ---------------------------------------------------------------------------
// write_acquisition_json
// ---------------------------------------------------------------------------
void write_acquisition_json(const std::string& path, const AcquisitionProvenance& a) {
    auto j = acquisition_to_json(a);

    // Create parent directories if needed.
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }

    std::ofstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("AcquisitionIo: cannot write file: " + path);
    }
    f << j.dump(2) << "\n";
}

}  // namespace io
}  // namespace ads1292
