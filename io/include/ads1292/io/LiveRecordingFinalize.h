#pragma once
// io/include/ads1292/io/LiveRecordingFinalize.h
// Persist a just-acquired live recording: CSV -> JSON bundle + optional HDF5.
// Qt-free; testable headless.
// Namespace: ads1292::io
//
// Provenance simplification: the Python oracle's _finalize_recording calls
// finalize_acquisition_provenance() which adds measured-effective-rate attrs
// (effective_sample_rate_hz, wall_clock_seconds) derived from the worker's
// monotonic first/last sample timestamps. Those timestamps are not available
// at the io layer, so this simplified provenance omits them. The acquisition
// section written to the bundle is still valid per the schema.

#include <optional>
#include <string>
#include <vector>
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/TestProtocol.h"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/dsp/LiveCalibration.h"

namespace ads1292 {
namespace io {

/// Options controlling what finalize_live_recording writes.
///
/// `protocol` and `quality_gate` default-construct to their zero-value forms.
/// To use the canonical MOTAC defaults, set them from the io template helpers:
///   opt.protocol     = ads1292::io::protocol_template();
///   opt.quality_gate = ads1292::io::quality_gate_template();
struct FinalizeOptions {
  ads1292::SessionMetadata           metadata;
  std::vector<ads1292::EventMarker>  events;
  ads1292::Calibration               calibration;
  ads1292::TestProtocol              protocol;        ///< use protocol_template() for MOTAC defaults
  ads1292::dsp::QualityGate          quality_gate;    ///< use quality_gate_template() for defaults
  /// When set, written into the bundle's acquisition.live_calibration JSON object.
  /// Mirrors Python build_acquisition_provenance(live_calibration=...) path.
  std::optional<ads1292::LiveStreamCalibration> live_calibration;
  std::string acquisition_mode = "live_stream";
  std::string port;
  std::string started_at;          ///< ISO 8601 string, or "" if unavailable
  double sample_rate_hz = 500.0;
  bool write_h5 = true;
  bool write_xlsx = false;         ///< Write XLSX alongside the CSV (convenience export; off by default)
  std::string created_at;          ///< ISO 8601 finalize timestamp, or ""
};

/// Result returned by finalize_live_recording.
struct FinalizeResult {
  bool wrote = false;         ///< false if the CSV had 0 samples (empty capture)
  int sample_count = 0;
  std::string csv_path;
  std::string bundle_path;    ///< path to the written .json bundle (empty on skip)
  std::string h5_path;        ///< path to the written .h5 file (empty when write_h5=false or skip)
  std::string xlsx_path;      ///< path to the written .xlsx file (empty when write_xlsx=false or skip)
};

/// Read the CSV that the acquisition engine wrote, build a simplified
/// AcquisitionProvenance, and persist the recording bundle (.json) plus,
/// optionally, the HDF5 file.
///
/// Empty-capture guard: if the CSV contains 0 data samples, returns
/// FinalizeResult{wrote=false} and does NOT write any sidecar files.
///
/// Thread-safe: reads only the csv_path and opt arguments; no shared state.
FinalizeResult finalize_live_recording(const std::string& csv_path,
                                       const FinalizeOptions& opt);

}  // namespace io
}  // namespace ads1292
