#pragma once
#include <string>
#include "ads1292/model/EventMarker.h"

namespace ads1292 {
struct EventSampleIndices {
  int start_sample_index = 0;
  int end_sample_index = 0;
  int duration_samples = 0;
};

int seconds_to_sample_index(double seconds, double sample_rate_hz);
EventSampleIndices event_sample_indices(const EventMarker& e, double sample_rate_hz);
std::string slug(const std::string& value);
std::string event_id(const EventMarker& e, double sample_rate_hz);
}  // namespace ads1292
