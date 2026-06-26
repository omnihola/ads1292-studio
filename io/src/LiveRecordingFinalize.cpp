// io/src/LiveRecordingFinalize.cpp
// Implementation of finalize_live_recording.
// Mirrors Python AcquisitionController._finalize_recording in controller.py.
// Qt-free; testable headless.

#include "ads1292/io/LiveRecordingFinalize.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/Bundle.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/io/ProcessingIo.h"
#include "ads1292/io/XlsxIo.h"

#ifdef ADS1292_HAVE_HDF5
#include "ads1292/io/H5Io.h"
#endif

#include <filesystem>
#include <string>

namespace fs = std::filesystem;

namespace ads1292 {
namespace io {

FinalizeResult finalize_live_recording(const std::string& csv_path,
                                       const FinalizeOptions& opt) {
  // Step 1: Read the CSV the acquisition engine wrote.
  auto samples = ads1292::io::read_recording_csv(csv_path);

  // Empty-capture guard (mirrors Python: "0 samples -> nothing finalized").
  if (samples.empty()) {
    return {false, 0, csv_path, "", "", ""};
  }

  // Step 2: Build a simplified AcquisitionProvenance.
  //
  // SIMPLIFICATION vs Python oracle: finalize_acquisition_provenance() in
  // acquisition.py also populates effective_sample_rate_hz and
  // wall_clock_seconds from the worker's monotonic timestamps. Those
  // timestamps are not available at the io layer, so this C++ port omits
  // those attrs. The acquisition section written to the bundle remains valid
  // per the ads1292-acquisition-provenance-v1 schema.
  ads1292::io::AcquisitionProvenance a;
  a.csv_name         = fs::path(csv_path).filename().string();
  a.acquisition_mode = opt.acquisition_mode;
  a.port             = opt.port;
  a.started_at       = opt.started_at;
  a.sample_rate_hz   = opt.sample_rate_hz;
  // Wire live_calibration: when present, serialize the normalized calibration
  // into the acquisition provenance's live_calibration JSON object.
  // Mirrors Python build_acquisition_provenance(live_calibration=...) path.
  if (opt.live_calibration) {
      a.live_calibration = live_calibration_to_json(opt.live_calibration->normalized());
  }
  a = a.normalized();

  // Step 3: Build processing settings (no sample_rate_hz arg — the function
  // returns the canonical default RecordingProcessingSettings).
  auto processing = ads1292::io::build_processing_settings();

  // Step 4: Write the recording bundle (.json sidecar alongside the CSV).
  auto bundle_path = ads1292::io::write_recording_bundle(
      csv_path,
      opt.metadata,
      opt.events,
      opt.calibration,
      a,
      opt.protocol,
      opt.quality_gate,
      processing,
      opt.sample_rate_hz,
      opt.created_at);

  // Step 5: Optionally write HDF5.
  std::string h5_path;

#ifdef ADS1292_HAVE_HDF5
  if (opt.write_h5) {
    // Build the bundle JSON string (reuse the same args as write_recording_bundle
    // but call build_recording_bundle which returns nlohmann::ordered_json).
    auto bundle_json = ads1292::io::build_recording_bundle(
        a.csv_name,
        opt.metadata,
        opt.events,
        opt.calibration,
        a,
        opt.protocol,
        opt.quality_gate,
        processing,
        opt.sample_rate_hz,
        opt.created_at).dump(2);

    h5_path = (fs::path(csv_path).parent_path() /
               (fs::path(csv_path).stem().string() + ".h5")).string();

    ads1292::io::H5Attrs attrs;
    attrs.csv_name       = a.csv_name;
    attrs.created_at     = opt.created_at;
    attrs.sample_rate_hz = std::to_string(opt.sample_rate_hz);
    attrs.sample_count   = std::to_string(samples.size());
    // attrs.schema left empty: write_recording_h5 defaults it to "ads1292-h5/1"

    ads1292::io::write_recording_h5(h5_path, samples, bundle_json, attrs);
  }
#endif

  // Step 6: Optionally write XLSX.
  std::string xlsx_path;
  if (opt.write_xlsx) {
    xlsx_path = recording_xlsx_path(csv_path);
    write_recording_xlsx(csv_path, opt.events, opt.sample_rate_hz);
  }

  return {true, static_cast<int>(samples.size()), csv_path, bundle_path, h5_path, xlsx_path};
}

}  // namespace io
}  // namespace ads1292
