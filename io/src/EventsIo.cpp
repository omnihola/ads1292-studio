// io/src/EventsIo.cpp
#include "ads1292/io/EventsIo.h"
#include "ads1292/event/EventId.h"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {

// ---- Schema constants ----
static const char* EVENT_ANNOTATIONS_SCHEMA   = "ads1292-event-annotations-v1";
static const char* EVENT_TIMESTAMP_REFERENCE  = "relative_seconds_from_recording_start";
static const char* EVENT_SAMPLE_INDEX_REFERENCE = "zero_based_sample_index_at_recording_sample_rate";
static const double DEFAULT_EVENT_SAMPLE_RATE_HZ = 500.0;

// ---- helpers ----
namespace {
double normalize_sample_rate(double sr) {
  return (sr > 0.0) ? sr : DEFAULT_EVENT_SAMPLE_RATE_HZ;
}
}  // namespace

// ---- read_events_json ----
std::vector<ads1292::EventMarker> read_events_json(const std::string& path) {
  std::ifstream f(path);
  if (!f.is_open()) {
    throw std::runtime_error("EventsIo: cannot open file: " + path);
  }

  nlohmann::json root;
  f >> root;

  // The root may be an object with an "events" array, or a bare array.
  const nlohmann::json* arr_ptr = nullptr;
  nlohmann::json bare;  // storage if root is already the array

  if (root.is_object() && root.contains("events") && root["events"].is_array()) {
    arr_ptr = &root["events"];
  } else if (root.is_array()) {
    arr_ptr = &root;
  } else {
    // Return empty — nothing to parse.
    return {};
  }

  std::vector<ads1292::EventMarker> result;
  for (const auto& item : *arr_ptr) {
    if (!item.is_object()) {
      continue;  // skip non-object entries
    }

    // Forgiving timestamp: timestamp_seconds ?? start_seconds ?? 0.0
    double timestamp = 0.0;
    if (item.contains("timestamp_seconds") && item["timestamp_seconds"].is_number()) {
      timestamp = item["timestamp_seconds"].get<double>();
    } else if (item.contains("start_seconds") && item["start_seconds"].is_number()) {
      timestamp = item["start_seconds"].get<double>();
    }

    // Forgiving duration:
    //   - if duration_seconds present and numeric → use it directly
    //   - else derive from start_seconds/end_seconds
    double duration = 0.0;
    if (item.contains("duration_seconds") && item["duration_seconds"].is_number()) {
      duration = item["duration_seconds"].get<double>();
    } else {
      double start = timestamp;
      if (item.contains("start_seconds") && item["start_seconds"].is_number()) {
        start = item["start_seconds"].get<double>();
      }
      double end = start;
      if (item.contains("end_seconds") && item["end_seconds"].is_number()) {
        end = item["end_seconds"].get<double>();
      }
      duration = std::max(0.0, end - start);
      timestamp = start;
    }

    std::string label;
    if (item.contains("label") && item["label"].is_string()) {
      label = item["label"].get<std::string>();
    }

    std::string notes;
    if (item.contains("notes") && item["notes"].is_string()) {
      notes = item["notes"].get<std::string>();
    }

    result.push_back(
        ads1292::EventMarker{timestamp, label, notes, duration}.normalized());
  }

  return result;
}

// ---- write_events_json ----
void write_events_json(const std::string& path,
                       const std::vector<ads1292::EventMarker>& events,
                       double sample_rate_hz) {
  double sr = normalize_sample_rate(sample_rate_hz);

  // Build the events array.
  nlohmann::ordered_json events_arr = nlohmann::ordered_json::array();
  for (const auto& event : events) {
    auto m   = event.normalized();
    auto idx = ads1292::event_sample_indices(m, sr);

    nlohmann::ordered_json entry;
    entry["event_id"]           = ads1292::event_id(m, sr);
    entry["timestamp_seconds"]  = m.timestamp_seconds;
    entry["start_seconds"]      = m.timestamp_seconds;
    entry["end_seconds"]        = m.end_seconds();
    entry["duration_seconds"]   = m.duration_seconds;
    entry["start_sample_index"] = idx.start_sample_index;
    entry["end_sample_index"]   = idx.end_sample_index;
    entry["duration_samples"]   = idx.duration_samples;
    entry["event_type"]         = m.is_interval() ? "interval" : "point";
    entry["label"]              = m.label;
    entry["notes"]              = m.notes;

    events_arr.push_back(std::move(entry));
  }

  // Build the top-level payload.
  nlohmann::ordered_json payload;
  payload["schema"]                 = EVENT_ANNOTATIONS_SCHEMA;
  payload["timestamp_reference"]    = EVENT_TIMESTAMP_REFERENCE;
  payload["sample_rate_hz"]         = sr;
  payload["sample_index_reference"] = EVENT_SAMPLE_INDEX_REFERENCE;
  payload["events"]                 = std::move(events_arr);

  // Create parent directories if needed.
  auto parent = std::filesystem::path(path).parent_path();
  if (!parent.empty()) {
    std::filesystem::create_directories(parent);
  }

  std::ofstream f(path);
  if (!f.is_open()) {
    throw std::runtime_error("EventsIo: cannot write file: " + path);
  }
  f << payload.dump(2) << "\n";
}

// ---- event_template ----
std::vector<ads1292::EventMarker> event_template() {
  return {
    ads1292::EventMarker{5.0,  "motion",      "subject moved arm",      3.0},
    ads1292::EventMarker{20.0, "deep breath",  "respiration challenge",  5.0},
  };
}

}  // namespace io
}  // namespace ads1292
