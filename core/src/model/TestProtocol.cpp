// core/src/model/TestProtocol.cpp
#include "ads1292/model/TestProtocol.h"
#include <algorithm>
#include <string>

namespace ads1292 {

namespace {

/// Trim leading/trailing ASCII whitespace from s.
static std::string trim(const std::string& s) {
    const auto is_ws = [](unsigned char c) {
        return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
    };
    auto begin = s.begin();
    while (begin != s.end() && is_ws(static_cast<unsigned char>(*begin)))
        ++begin;
    auto end = s.end();
    while (end != begin && is_ws(static_cast<unsigned char>(*(end - 1))))
        --end;
    return std::string(begin, end);
}

/// Trim value; if empty after trim, return fallback.
static std::string clean(const std::string& value, const std::string& fallback) {
    const std::string t = trim(value);
    return t.empty() ? fallback : t;
}

} // namespace

ProtocolStep ProtocolStep::normalized() const {
    ProtocolStep n;
    n.start_seconds    = std::max(0.0, start_seconds);
    n.duration_seconds = std::max(0.0, duration_seconds);
    n.label            = clean(label,       "step");
    n.instruction      = clean(instruction, "Follow the protocol step.");
    return n;
}

TestProtocol TestProtocol::normalized() const {
    TestProtocol n;
    n.name                  = clean(name,                  "ADS1292 validation protocol");
    n.objective             = trim(objective);  // no fallback
    n.operator_instructions = clean(operator_instructions, "Follow the listed protocol steps.");
    n.acceptance_notes      = clean(acceptance_notes,      "Review quality gate and artifacts before accepting the run.");
    n.steps.reserve(steps.size());
    for (const auto& s : steps) {
        n.steps.push_back(s.normalized());
    }
    return n;
}

} // namespace ads1292
