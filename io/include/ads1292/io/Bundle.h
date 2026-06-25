#pragma once
#include <optional>
#include <string>
#include <vector>
#include "nlohmann/json.hpp"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/EventMarker.h"

namespace ads1292 {
namespace io {

// ── SessionMetadata ────────────────────────────────────────────────────────
struct SessionMetadata {
  std::string operator_        = "";
  std::string subject_id       = "untitled";
  std::string session_id       = "untitled-session";
  std::string montage          = "RA/LA/RL torso";
  std::string electrode        = "unspecified electrode";
  std::string acquisition_mode = "live_stream";
  std::string notes            = "";
};

// ── QualityGate ────────────────────────────────────────────────────────────
struct QualityGate {
  double min_duration_seconds   = 8.0;
  double min_contact_ok_percent = 95.0;
  int    min_r_peaks            = 5;
  double min_hr_bpm             = 35.0;
  double max_hr_bpm             = 180.0;
  bool   require_qrs_clear      = true;
  std::optional<double> max_baseline_drift_counts;  // null in golden
  std::optional<double> max_noise_rms_counts;       // null in golden
  std::optional<double> max_peak_to_peak_counts;    // null in golden
};

// ── RecordingProcessingSettings ───────────────────────────────────────────
struct RecordingProcessingSettings {
  double gain               = 1.0;
  int    sweep_speed_mm_s   = 25;
  double time_window_seconds = 8.0;
  bool   bandpass_enabled   = false;
  bool   highpass_enabled   = false;
  double highpass_hz        = 0.5;
  bool   lowpass_enabled    = false;
  double lowpass_hz         = 40.0;
  bool   notch_enabled      = false;
  double notch_hz           = 60.0;
  bool   ecg_inverted       = false;
  int    smoothing_window   = 11;
  std::string processing_notes = "display settings only; raw CSV samples are unchanged";
  double sample_rate_hz     = 500.0;
  std::string schema        = "ads1292-processing-settings-v1";
};

// ── TestProtocol ──────────────────────────────────────────────────────────
struct ProtocolStep {
  std::string name        = "";
  std::string description = "";
};

struct TestProtocol {
  std::string name                 = "ADS1292 validation protocol";
  std::string objective            = "";
  std::string operator_instructions = "Follow the listed protocol steps.";
  std::string acceptance_notes     = "Review quality gate and artifacts before accepting the run.";
  std::vector<ProtocolStep> steps;
};

// ── AcquisitionProvenance ─────────────────────────────────────────────────
struct AcquisitionProvenance {
  std::string acquisition_mode = "live_stream";
  std::string port             = "";
  std::string started_at       = "";
  std::string csv_name         = "";
  std::string csv_schema       = "ads1292-studio-live-stream-v1";
  std::string schema           = "ads1292-acquisition-provenance-v1";
  std::string timestamp_reference = "relative_seconds_from_recording_start";
};

// ── payload functions ─────────────────────────────────────────────────────
nlohmann::json events_payload(const std::vector<EventMarker>& events, double sample_rate_hz);
nlohmann::json metadata_payload(const SessionMetadata& meta);
nlohmann::json calibration_payload(const Calibration& cal);
nlohmann::json quality_gate_payload(const QualityGate& gate);
nlohmann::json processing_payload(const RecordingProcessingSettings& ps);
nlohmann::json protocol_payload(const TestProtocol& proto);
nlohmann::json acquisition_payload(const AcquisitionProvenance& prov, double sample_rate_hz);

}  // namespace io
}  // namespace ads1292
