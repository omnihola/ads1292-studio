#include "ads1292/view/EventLog.h"
#include <algorithm>

namespace ads1292::view {

void EventLog::add_point(double timestamp_seconds, const std::string& label,
                         const std::string& notes) {
  EventMarker marker{timestamp_seconds, label, notes, 0.0};
  events_.push_back(marker.normalized());
}

void EventLog::start_range(double timestamp_seconds) {
  pending_ = timestamp_seconds;
}

bool EventLog::end_range(double timestamp_seconds, const std::string& label,
                         const std::string& notes) {
  if (!pending_ || timestamp_seconds <= *pending_) {
    return false;
  }
  EventMarker marker{*pending_, label, notes,
                     timestamp_seconds - *pending_};
  events_.push_back(marker.normalized());
  pending_.reset();
  return true;
}

void EventLog::add_manual_range(double start_seconds, double end_seconds,
                                const std::string& label,
                                const std::string& notes) {
  double duration = std::max(0.0, end_seconds - start_seconds);
  EventMarker marker{start_seconds, label, notes, duration};
  events_.push_back(marker.normalized());
}

bool EventLog::remove_last() {
  if (events_.empty()) {
    return false;
  }
  events_.pop_back();
  return true;
}

bool EventLog::remove_at(std::size_t index) {
  if (index >= events_.size()) {
    return false;
  }
  events_.erase(events_.begin() + index);
  return true;
}

const std::vector<EventMarker>& EventLog::events() const {
  return events_;
}

std::optional<double> EventLog::pending_range_start() const {
  return pending_;
}

}  // namespace ads1292::view
