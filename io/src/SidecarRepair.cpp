// io/src/SidecarRepair.cpp
// Port of session_index.py: _expected_sidecar_path / _sidecar_label /
// _template_path_for / build_sidecar_completion_plan / SidecarPlanRow /
// write_sidecar_template_bundle / write_sidecar_apply_script.
// Pure C++17 — no Qt.
//
// NOTE: The acquisition sidecar template is a SIMPLIFIED default.
// Python _acquisition_template() calls build_acquisition_provenance() with
// calibration + live_calibration arguments that are not ported.  Instead we
// write a minimal AcquisitionProvenance (csv_name, port="review-required",
// started_at="review-required", sample_rate_hz=500.0) and call .normalized().
// This still produces a fully valid, parseable acquisition sidecar.
#include "ads1292/io/SidecarRepair.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/io/CalibrationIo.h"
#include "ads1292/io/EventsIo.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/ProcessingIo.h"
#include "ads1292/io/ProtocolIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/model/SessionMetadata.h"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

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

/// POSIX single-quote escaping — matches Python shlex.quote.
/// Wraps s in single quotes; any literal ' inside becomes '\''
std::string shell_quote(const std::string& s) {
    std::string r;
    r += '\'';
    for (char c : s) {
        if (c == '\'') r += "'\\''";
        else           r += c;
    }
    r += '\'';
    return r;
}

/// Write a template sidecar at path for the given row and sidecar type.
/// Reuses the P7b sidecar writers/templates.  For "acquisition" see the
/// module-level NOTE about the simplified default.
void write_sidecar_template_impl(const std::string& path,
                                  const ads1292::index::SessionIndexRow& row,
                                  const std::string& sidecar)
{
    if (sidecar == "metadata") {
        ads1292::SessionMetadata m;
        m.session_id = row.session_id;
        m.subject_id = row.subject_id;
        m.electrode  = row.electrode;
        m.montage    = row.montage;
        m.operator_  = row.operator_;
        m.notes      = "Review and complete this generated metadata sidecar before packaging.";
        ads1292::io::write_metadata_json(path, m);
        return;
    }
    if (sidecar == "events") {
        ads1292::io::write_events_json(path, ads1292::io::event_template());
        return;
    }
    if (sidecar == "calibration") {
        ads1292::io::write_calibration_json(path, ads1292::io::calibration_template());
        return;
    }
    if (sidecar == "acquisition") {
        // SIMPLIFIED: build_acquisition_provenance() with calibration/live_calibration not ported.
        ads1292::io::AcquisitionProvenance a;
        a.csv_name       = fs::path(row.path).filename().string();
        a.port           = "review-required";
        a.started_at     = "review-required";
        a.sample_rate_hz = 500.0;
        ads1292::io::write_acquisition_json(path, a.normalized());
        return;
    }
    if (sidecar == "protocol") {
        ads1292::io::write_protocol_json(path, ads1292::io::protocol_template());
        return;
    }
    if (sidecar == "quality_gate") {
        ads1292::io::write_quality_gate_json(path, ads1292::io::quality_gate_template());
        return;
    }
    if (sidecar == "processing") {
        ads1292::io::write_processing_json(path, ads1292::io::build_processing_settings());
        return;
    }
    // Unknown sidecar type: no-op (no template writer available)
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

std::vector<std::string> write_sidecar_template_bundle(
    const std::string& template_dir,
    const std::vector<ads1292::index::SessionIndexRow>& rows)
{
    std::vector<std::string> written;
    for (const auto& row : rows) {
        for (const auto& sidecar : split_skip_empty(row.missing_sidecars, ';')) {
            const std::string path =
                template_path_for(template_dir, row.relative_path, row.path, sidecar);
            fs::create_directories(fs::path(path).parent_path());
            write_sidecar_template_impl(path, row, sidecar);
            written.push_back(path);
        }
    }
    return written;
}

void write_sidecar_apply_script(const std::string& path,
                                 const std::vector<SidecarPlanRow>& plan)
{
    std::vector<std::string> lines = {
        "#!/bin/sh",
        "set -eu",
        "",
        "# Generated by ADS1292 Studio.",
        "# Review generated sidecar templates before running this script.",
        "# Existing target sidecars are left untouched by cp -n.",
        "",
    };

    if (plan.empty()) {
        lines.push_back("echo 'No missing sidecars to apply.'");
    }

    for (const auto& row : plan) {
        // Resolve paths (weakly_canonical handles non-existent paths gracefully,
        // matching Python's Path.resolve() behaviour).
        const auto template_path = fs::weakly_canonical(fs::path(row.template_path));
        const auto target_path   = fs::weakly_canonical(fs::path(row.target_path));

        lines.push_back("# " + row.relative_path + ": " + row.sidecar);
        lines.push_back("mkdir -p " + shell_quote(target_path.parent_path().string()));
        lines.push_back("cp -n " + shell_quote(template_path.string()) +
                        " " + shell_quote(target_path.string()));
        lines.push_back("");
    }

    // Write: join lines with '\n', then append a final '\n'.
    std::ofstream f(path);
    if (!f.is_open()) {
        throw std::runtime_error("write_sidecar_apply_script: cannot open " + path);
    }
    for (const auto& line : lines) {
        f << line << '\n';
    }
    f.close();

    // chmod 0755 — matches Python script_path.chmod(0o755)
    fs::permissions(fs::path(path),
        fs::perms::owner_read  | fs::perms::owner_write | fs::perms::owner_exec |
        fs::perms::group_read  | fs::perms::group_exec  |
        fs::perms::others_read | fs::perms::others_exec,
        fs::perm_options::replace);
}

}  // namespace io
}  // namespace ads1292
