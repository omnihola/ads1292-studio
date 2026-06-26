// gui/src/RecordingPaths.cpp
// Timestamped recording path helper.
// Pure C++17; no Qt dependency.

#include "ads1292/gui/RecordingPaths.h"

#include <chrono>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <iomanip>
#include <sstream>

namespace ads1292 {
namespace gui {

std::string timestamped_recording_csv_path(const std::string& mode,
                                            const std::string& base_dir) {
    // Determine base directory
    std::string dir = base_dir;
    if (dir.empty()) {
        const char* home = std::getenv("HOME");
        std::string home_str = home ? home : "/tmp";
        dir = (std::filesystem::path(home_str) / "Documents" / "ECG" / mode).string();
    }

    // Generate local timestamp
    auto now = std::chrono::system_clock::now();
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    struct tm tm_local{};
    localtime_r(&t, &tm_local);

    std::ostringstream oss;
    oss << std::put_time(&tm_local, "%Y-%m-%d-%H%M%S");
    oss << "-ads1292-studio.csv";

    return (std::filesystem::path(dir) / oss.str()).string();
}

std::string current_iso8601_string() {
    auto now = std::chrono::system_clock::now();
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    struct tm tm_local{};
    localtime_r(&t, &tm_local);
    std::ostringstream oss;
    oss << std::put_time(&tm_local, "%Y-%m-%dT%H:%M:%S");
    return oss.str();
}

}  // namespace gui
}  // namespace ads1292
