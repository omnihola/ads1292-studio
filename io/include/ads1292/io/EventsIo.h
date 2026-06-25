// io/include/ads1292/io/EventsIo.h
#pragma once
#include <string>
#include <vector>
#include "ads1292/model/EventMarker.h"

namespace ads1292 {
namespace io {

/// Read the events array from the JSON file at @p path.
/// The root may be an object with an "events" array, or a bare array.
/// Each object item is parsed forgivingly (timestamp/start/end/duration fallbacks).
/// Returns normalized EventMarkers. Unknown keys are ignored; missing keys keep defaults.
/// Throws std::runtime_error if the file cannot be opened.
std::vector<ads1292::EventMarker> read_events_json(const std::string& path);

/// Write @p events as a schema-annotated pretty-printed JSON to @p path at @p sample_rate_hz.
/// Each entry includes event_id, sample indices, event_type, label, and notes.
/// Parent directories are created as needed.
void write_events_json(const std::string& path,
                       const std::vector<ads1292::EventMarker>& events,
                       double sample_rate_hz = 500.0);

/// Return the canonical event template markers.
std::vector<ads1292::EventMarker> event_template();

}  // namespace io
}  // namespace ads1292
