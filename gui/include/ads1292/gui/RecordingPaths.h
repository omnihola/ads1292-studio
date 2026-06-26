#pragma once
// gui/include/ads1292/gui/RecordingPaths.h
// Timestamped recording path helper + ISO-8601 timestamp utility.
// Pure C++17; no Qt dependency — testable headless.
// Namespace: ads1292::gui

#include <string>

namespace ads1292 {
namespace gui {

/// Return a timestamped CSV path for a new live recording.
///
/// Format: <base_dir>/<YYYY-MM-DD-HHMMSS>-ads1292-studio.csv
///
/// If base_dir is empty, defaults to $HOME/Documents/ECG/<mode>.
/// Does NOT create the parent directory — the caller is responsible.
///
/// The path is deterministic given an explicit base_dir and a fixed clock
/// instant, so tests pass a temp dir and verify the suffix.
std::string timestamped_recording_csv_path(const std::string& mode,
                                            const std::string& base_dir = "");

/// Return the current local time formatted as an ISO-8601-like string:
///   YYYY-MM-DDTHH:MM:SS
/// Used to populate FinalizeOptions::started_at.
std::string current_iso8601_string();

}  // namespace gui
}  // namespace ads1292
