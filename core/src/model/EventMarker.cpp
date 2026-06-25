// core/src/model/EventMarker.cpp
#include "ads1292/model/EventMarker.h"
#include <algorithm>
#include <cctype>

namespace ads1292 {
namespace {
std::string strip(const std::string& s) {
  size_t b = 0, e = s.size();
  while (b < e && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
  while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) --e;
  return s.substr(b, e - b);
}
}  // namespace

EventMarker EventMarker::normalized() const {
  EventMarker out;
  out.timestamp_seconds = std::max(0.0, timestamp_seconds);
  out.duration_seconds = std::max(0.0, duration_seconds);
  std::string trimmed_label = strip(label);
  out.label = trimmed_label.empty() ? "event" : trimmed_label;
  out.notes = strip(notes);
  return out;
}

double EventMarker::end_seconds() const {
  EventMarker n = normalized();
  return n.timestamp_seconds + n.duration_seconds;
}

bool EventMarker::is_interval() const {
  return normalized().duration_seconds > 0.0;
}
}  // namespace ads1292
