// io/src/BatchScan.cpp
#include "ads1292/io/BatchScan.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/RecordingBundle.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/model/SessionMetadata.h"

#include <filesystem>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace ads1292 {
namespace io {

namespace {

/// Mirrors batch.py _metadata_for:
///   1. Bundle short-circuit: if .json beside csv IS a recording bundle → extract metadata.
///   2. <stem>.json sidecar if present → read_metadata_json.
///   3. Otherwise → SessionMetadata{session_id=stem}.normalized().
ads1292::SessionMetadata _metadata_for(const fs::path& csv_path) {
    auto bundle_path = recording_bundle_path(csv_path.string());
    if (is_recording_bundle_path(bundle_path)) {
        return metadata_from_bundle(read_recording_bundle(bundle_path));
    }
    fs::path sidecar = fs::path(csv_path).replace_extension(".json");
    if (fs::exists(sidecar)) {
        return read_metadata_json(sidecar.string());  // propagate on corrupt sidecar
    }
    ads1292::SessionMetadata m;
    m.session_id = csv_path.stem().string();
    return m.normalized();
}

}  // anonymous namespace

// ── aggregate_recordings ──────────────────────────────────────────────────
std::vector<ads1292::index::BatchRow> aggregate_recordings(
    const std::vector<std::string>& csv_paths)
{
    constexpr double SAMPLE_RATE = 500.0;

    std::vector<ads1292::index::BatchRow> rows;
    rows.reserve(csv_paths.size());

    for (const auto& path_str : csv_paths) {
        fs::path csv_path(path_str);
        std::vector<ads1292::StreamSample> samples;
        ads1292::SessionMetadata metadata;
        ads1292::dsp::QualityMetrics metrics;

        try {
            samples = read_recording_csv(path_str);
            if (samples.empty()) continue;
            metadata = _metadata_for(csv_path);
            metrics = ads1292::dsp::compute_quality_metrics(samples, SAMPLE_RATE, "Auto");
        } catch (...) {
            continue;  // skip unreadable / problematic recordings
        }

        ads1292::index::BatchRow row;
        row.path                = path_str;
        row.session_id          = metadata.session_id;
        row.subject_id          = metadata.subject_id;
        row.electrode           = metadata.electrode;
        row.montage             = metadata.montage;
        row.sample_count        = metrics.sample_count;
        row.duration_seconds    = metrics.duration_seconds;
        row.ecg_source          = metrics.ecg_source;
        row.contact_ok_percent  = metrics.contact_ok_percent;
        row.r_peaks             = metrics.r_peaks;
        row.hr_median_bpm       = metrics.hr_median_bpm;
        row.qrs_clear           = metrics.qrs_clear;
        row.p_tentative         = metrics.p_tentative;
        row.t_tentative         = metrics.t_tentative;
        row.quality_label       = ads1292::dsp::quality_label(metrics);

        rows.push_back(std::move(row));
    }

    return rows;
}

}  // namespace io
}  // namespace ads1292
