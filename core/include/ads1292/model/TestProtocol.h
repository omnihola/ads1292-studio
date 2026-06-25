#pragma once
// core/include/ads1292/model/TestProtocol.h
// Protocol step + test protocol model structs.
// Pure C++17 — no Qt, no nlohmann in this header. JSON I/O lives in io/ProtocolIo.

#include <string>
#include <vector>

namespace ads1292 {

/// A single timed step in a test protocol.
struct ProtocolStep {
    double      start_seconds    = 0.0;
    double      duration_seconds = 0.0;
    std::string label;
    std::string instruction;

    /// Return a copy with fields clamped/cleaned:
    /// - start_seconds    = max(0, start_seconds)
    /// - duration_seconds = max(0, duration_seconds)
    /// - label            = trimmed, falls back to "step" if empty
    /// - instruction      = trimmed, falls back to "Follow the protocol step." if empty
    ProtocolStep normalized() const;
};

/// A complete test protocol (name, objective, ordered steps, notes).
struct TestProtocol {
    std::string              name                  = "ADS1292 validation protocol";
    std::string              objective;
    std::string              operator_instructions = "Follow the listed protocol steps.";
    std::vector<ProtocolStep> steps;
    std::string              acceptance_notes      = "Review quality gate and artifacts before accepting the run.";

    /// Return a copy with all fields normalized:
    /// - each step normalized via ProtocolStep::normalized()
    /// - name = trimmed, falls back to default if empty
    /// - objective = trimmed only (no fallback)
    /// - operator_instructions = trimmed, falls back to default if empty
    /// - acceptance_notes = trimmed, falls back to default if empty
    TestProtocol normalized() const;
};

} // namespace ads1292
