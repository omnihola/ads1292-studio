#pragma once
#include <vector>
#include "nlohmann/json.hpp"
#include "ads1292/model/EventMarker.h"

namespace ads1292 {
namespace io {
nlohmann::json events_payload(const std::vector<EventMarker>& events, double sample_rate_hz);
}  // namespace io
}  // namespace ads1292
