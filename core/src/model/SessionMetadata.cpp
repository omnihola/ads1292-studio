#include "ads1292/model/SessionMetadata.h"
#include <algorithm>
#include <cctype>

namespace ads1292 {
namespace {

// Trim leading/trailing ASCII whitespace.
std::string trim(const std::string& s) {
  auto first = s.begin();
  while (first != s.end() && std::isspace(static_cast<unsigned char>(*first))) {
    ++first;
  }
  auto last = s.end();
  while (last != first && std::isspace(static_cast<unsigned char>(*(last - 1)))) {
    --last;
  }
  return std::string(first, last);
}

// Return trimmed value, or fallback if result is empty.
std::string clean(const std::string& value, const std::string& fallback) {
  auto t = trim(value);
  return t.empty() ? fallback : t;
}

}  // namespace

SessionMetadata SessionMetadata::normalized() const {
  SessionMetadata n;
  n.session_id       = clean(session_id,       "untitled-session");
  n.subject_id       = clean(subject_id,       "anonymous");
  n.electrode        = clean(electrode,        "unspecified electrode");
  n.montage          = clean(montage,          "unspecified montage");
  n.operator_        = clean(operator_,        "unspecified operator");
  n.notes            = trim(notes);            // no fallback
  n.acquisition_mode = clean(acquisition_mode, "live_stream");
  return n;
}

}  // namespace ads1292
