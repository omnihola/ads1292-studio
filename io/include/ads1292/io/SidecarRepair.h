// io/include/ads1292/io/SidecarRepair.h
// Sidecar completion plan: SidecarPlanRow, build_sidecar_completion_plan,
// and the path helpers expected_sidecar_path / sidecar_label / template_path_for.
// Port of session_index.py: SidecarPlanRow / build_sidecar_completion_plan /
// _expected_sidecar_path / _sidecar_label / _template_path_for.
// Pure C++17, no Qt.
#pragma once
#include <string>
#include <vector>
#include "ads1292/index/SessionIndexRow.h"

namespace ads1292 {
namespace io {

/// A single row in the sidecar completion plan.
/// Matches Python SidecarPlanRow (paths stored as strings in C++).
struct SidecarPlanRow {
    std::string relative_path;
    std::string sidecar;
    std::string target_path;    // absolute path where the sidecar should live
    std::string template_path;  // path where the template will be written
    std::string suggested_action;
};

/// Returns the expected sidecar file path for a given csv_path and sidecar name.
/// Strips the trailing ".csv" suffix from csv_path and appends the sidecar suffix.
/// Matches Python _expected_sidecar_path(csv_path, sidecar).
std::string expected_sidecar_path(const std::string& csv_path, const std::string& sidecar);

/// Returns a human-readable label for the sidecar name ('_' → ' ').
/// Matches Python _sidecar_label(sidecar).
std::string sidecar_label(const std::string& sidecar);

/// Returns the path where the sidecar template should be written.
/// template_dir/<parent-of-relative_path>/<basename-of-expected-sidecar-path>
/// If parent of relative_path is "." or empty, omits the parent segment.
/// Matches Python _template_path_for(template_dir, row, sidecar).
std::string template_path_for(const std::string& template_dir,
                               const std::string& relative_path,
                               const std::string& csv_path,
                               const std::string& sidecar);

/// Build a sidecar completion plan from a list of session index rows.
/// For each row, splits missing_sidecars on ';' (skips empty tokens) and
/// produces a SidecarPlanRow for each missing sidecar.
/// Matches Python build_sidecar_completion_plan(rows, template_dir).
std::vector<SidecarPlanRow> build_sidecar_completion_plan(
    const std::vector<ads1292::index::SessionIndexRow>& rows,
    const std::string& template_dir);

}  // namespace io
}  // namespace ads1292
