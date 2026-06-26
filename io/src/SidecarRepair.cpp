// io/src/SidecarRepair.cpp
// Port of session_index.py: _expected_sidecar_path / _sidecar_label /
// _template_path_for / build_sidecar_completion_plan / SidecarPlanRow.
// Pure C++17 — no Qt, no nlohmann (pure logic layer).
#include "ads1292/io/SidecarRepair.h"
#include <filesystem>
#include <sstream>
#include <string>
#include <vector>

namespace ads1292 {
namespace io {

namespace {

/// Map sidecar name → file suffix, matching Python _expected_sidecar_path.
std::string sidecar_suffix(const std::string& sidecar) {
    if (sidecar == "metadata")     return ".json";
    if (sidecar == "events")       return ".events.json";
    if (sidecar == "calibration")  return ".calibration.json";
    if (sidecar == "acquisition")  return ".acquisition.json";
    if (sidecar == "protocol")     return ".protocol.json";
    if (sidecar == "quality_gate") return ".quality-gate.json";
    if (sidecar == "processing")   return ".processing.json";
    return "." + sidecar + ".json";
}

/// Split s on delim, returning only non-empty tokens.
std::vector<std::string> split_skip_empty(const std::string& s, char delim) {
    std::vector<std::string> tokens;
    std::stringstream ss(s);
    std::string token;
    while (std::getline(ss, token, delim)) {
        if (!token.empty())
            tokens.push_back(token);
    }
    return tokens;
}

}  // namespace

std::string expected_sidecar_path(const std::string& csv_path, const std::string& sidecar) {
    namespace fs = std::filesystem;
    const fs::path p(csv_path);
    // Strip the trailing .csv extension (stem = everything before the last ".csv")
    // and append the sidecar suffix.  Matches Python Path.with_suffix() semantics.
    const std::string new_name = p.stem().string() + sidecar_suffix(sidecar);
    return (p.parent_path() / new_name).string();
}

std::string sidecar_label(const std::string& sidecar) {
    std::string result = sidecar;
    for (char& c : result) {
        if (c == '_') c = ' ';
    }
    return result;
}

std::string template_path_for(const std::string& template_dir,
                               const std::string& relative_path,
                               const std::string& csv_path,
                               const std::string& sidecar) {
    namespace fs = std::filesystem;
    // Basename of the expected sidecar path for this csv/sidecar pair.
    const std::string target_name =
        fs::path(expected_sidecar_path(csv_path, sidecar)).filename().string();
    // Parent directory of the relative recording path.
    const fs::path parent = fs::path(relative_path).parent_path();
    const std::string parent_str = parent.string();
    if (parent_str.empty() || parent_str == ".") {
        return (fs::path(template_dir) / target_name).string();
    }
    return (fs::path(template_dir) / parent / target_name).string();
}

std::vector<SidecarPlanRow> build_sidecar_completion_plan(
    const std::vector<ads1292::index::SessionIndexRow>& rows,
    const std::string& template_dir)
{
    std::vector<SidecarPlanRow> plan;
    for (const auto& row : rows) {
        for (const auto& sidecar : split_skip_empty(row.missing_sidecars, ';')) {
            SidecarPlanRow pr;
            pr.relative_path    = row.relative_path;
            pr.sidecar          = sidecar;
            pr.target_path      = expected_sidecar_path(row.path, sidecar);
            pr.template_path    = template_path_for(template_dir, row.relative_path, row.path, sidecar);
            pr.suggested_action = "Create " + sidecar_label(sidecar) + " sidecar";
            plan.push_back(std::move(pr));
        }
    }
    return plan;
}

}  // namespace io
}  // namespace ads1292
