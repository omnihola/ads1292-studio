#pragma once
#include <string>

namespace ads1292 {
struct EventMarker {
  double timestamp_seconds = 0.0;
  std::string label = "event";
  std::string notes;
  double duration_seconds = 0.0;

  EventMarker normalized() const;
  double end_seconds() const;
  bool is_interval() const;
};
}  // namespace ads1292
