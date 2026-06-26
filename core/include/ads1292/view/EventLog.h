#pragma once
#include <vector>
#include <optional>
#include <string>
#include "ads1292/model/EventMarker.h"

namespace ads1292::view {
class EventLog {
 public:
  // Add a single event at a specific timestamp (zero-duration point).
  void add_point(double timestamp_seconds, const std::string& label,
                 const std::string& notes);

  // Begin recording a range event. Stores the start timestamp.
  void start_range(double timestamp_seconds);

  // End the current range event. Returns false if no pending start or if
  // end_seconds <= start_seconds.
  bool end_range(double timestamp_seconds, const std::string& label,
                 const std::string& notes);

  // Add a range event directly with explicit start and end.
  void add_manual_range(double start_seconds, double end_seconds,
                        const std::string& label, const std::string& notes);

  // Remove the last event. Returns false if the list is empty.
  bool remove_last();

  // Remove event at the given index. Returns false if index is out of range.
  bool remove_at(std::size_t index);

  // Clear all events and reset any pending range state.
  void clear();

  // Access the stored events.
  const std::vector<EventMarker>& events() const;

  // Get the pending range start timestamp, if any.
  std::optional<double> pending_range_start() const;

 private:
  std::vector<EventMarker> events_;
  std::optional<double> pending_;
};
}  // namespace ads1292::view
