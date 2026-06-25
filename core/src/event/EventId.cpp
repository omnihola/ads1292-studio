#include "ads1292/event/EventId.h"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include "ads1292/crypto/Sha1.h"

namespace ads1292 {
namespace {
double normalized_rate(double sr) { return sr > 0 ? sr : 500.0; }
}  // namespace

int seconds_to_sample_index(double seconds, double sample_rate_hz) {
  double idx = std::nearbyint(seconds * sample_rate_hz);  // round-half-to-even, matches Python round
  int v = static_cast<int>(idx);
  return v > 0 ? v : 0;
}

EventSampleIndices event_sample_indices(const EventMarker& e, double sample_rate_hz) {
  double sr = normalized_rate(sample_rate_hz);
  EventMarker m = e.normalized();
  EventSampleIndices out;
  out.start_sample_index = seconds_to_sample_index(m.timestamp_seconds, sr);
  out.end_sample_index = seconds_to_sample_index(m.end_seconds(), sr);
  out.duration_samples = std::max(0, out.end_sample_index - out.start_sample_index);
  return out;
}

std::string slug(const std::string& value) {
  std::string lower;
  for (char ch : value) lower.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
  // replace each run of non-[a-z0-9] with a single '-'
  std::string collapsed;
  bool in_run = false;
  for (char ch : lower) {
    bool keep = (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9');
    if (keep) { collapsed.push_back(ch); in_run = false; }
    else if (!in_run) { collapsed.push_back('-'); in_run = true; }
  }
  size_t b = collapsed.find_first_not_of('-');
  size_t e = collapsed.find_last_not_of('-');
  std::string trimmed = (b == std::string::npos) ? "" : collapsed.substr(b, e - b + 1);
  if (trimmed.size() > 32) trimmed = trimmed.substr(0, 32);
  return trimmed.empty() ? "event" : trimmed;
}

std::string event_id(const EventMarker& e, double sample_rate_hz) {
  double sr = normalized_rate(sample_rate_hz);
  EventMarker m = e.normalized();
  EventSampleIndices idx = event_sample_indices(m, sr);
  std::string type = m.is_interval() ? "interval" : "point";
  std::string fingerprint = std::to_string(idx.start_sample_index) + "|" +
                            std::to_string(idx.end_sample_index) + "|" + type + "|" +
                            m.label + "|" + m.notes;
  std::string digest = sha1_hex(fingerprint).substr(0, 8);
  char head[64];
  std::snprintf(head, sizeof(head), "evt-%07d-%07d-", idx.start_sample_index, idx.end_sample_index);
  return std::string(head) + slug(m.label) + "-" + digest;
}
}  // namespace ads1292
