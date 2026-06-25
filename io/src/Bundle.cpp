#include "ads1292/io/Bundle.h"
#include "ads1292/event/EventId.h"

namespace ads1292 {
namespace io {

static nlohmann::json event_entry(const EventMarker& event, double sample_rate_hz) {
  EventMarker m = event.normalized();
  EventSampleIndices idx = event_sample_indices(m, sample_rate_hz);
  std::string type = m.is_interval() ? "interval" : "point";
  return {
      {"event_id", event_id(m, sample_rate_hz)},
      {"timestamp_seconds", m.timestamp_seconds},
      {"start_seconds", m.timestamp_seconds},
      {"end_seconds", m.end_seconds()},
      {"duration_seconds", m.duration_seconds},
      {"start_sample_index", idx.start_sample_index},
      {"end_sample_index", idx.end_sample_index},
      {"duration_samples", idx.duration_samples},
      {"event_type", type},
      {"label", m.label},
      {"notes", m.notes},
  };
}

nlohmann::json events_payload(const std::vector<EventMarker>& events, double sample_rate_hz) {
  double sr = sample_rate_hz > 0 ? sample_rate_hz : 500.0;
  nlohmann::json entries = nlohmann::json::array();
  for (const auto& e : events) entries.push_back(event_entry(e, sr));
  return {
      {"schema", "ads1292-event-annotations-v1"},
      {"timestamp_reference", "relative_seconds_from_recording_start"},
      {"sample_index_reference", "zero_based_sample_index_at_recording_sample_rate"},
      {"sample_rate_hz", sr},
      {"events", entries},
  };
}

}  // namespace io
}  // namespace ads1292
