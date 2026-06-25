#include "ads1292/io/Bundle.h"
#include "ads1292/event/EventId.h"

namespace ads1292 {
namespace io {

// ── events_payload ────────────────────────────────────────────────────────

static nlohmann::json event_entry(const EventMarker& event, double sample_rate_hz) {
  EventMarker m = event.normalized();
  EventSampleIndices idx = event_sample_indices(m, sample_rate_hz);
  std::string type = m.is_interval() ? "interval" : "point";
  return {
      {"event_id", event_id(m, sample_rate_hz)},
      {"timestamp_seconds", m.timestamp_seconds},
      {"start_seconds", m.timestamp_seconds},
      {"end_seconds", m.end_seconds()},
      {"duration_seconds", m.duration_seconds},
      {"start_sample_index", idx.start_sample_index},
      {"end_sample_index", idx.end_sample_index},
      {"duration_samples", idx.duration_samples},
      {"event_type", type},
      {"label", m.label},
      {"notes", m.notes},
  };
}

nlohmann::json events_payload(const std::vector<EventMarker>& events, double sample_rate_hz) {
  double sr = sample_rate_hz > 0 ? sample_rate_hz : 500.0;
  nlohmann::json entries = nlohmann::json::array();
  for (const auto& e : events) entries.push_back(event_entry(e, sr));
  return {
      {"schema", "ads1292-event-annotations-v1"},
      {"timestamp_reference", "relative_seconds_from_recording_start"},
      {"sample_index_reference", "zero_based_sample_index_at_recording_sample_rate"},
      {"sample_rate_hz", sr},
      {"events", entries},
  };
}

// ── metadata_payload ──────────────────────────────────────────────────────

nlohmann::json metadata_payload(const SessionMetadata& meta) {
  return {
      {"operator",         meta.operator_},
      {"subject_id",       meta.subject_id},
      {"session_id",       meta.session_id},
      {"montage",          meta.montage},
      {"electrode",        meta.electrode},
      {"acquisition_mode", meta.acquisition_mode},
      {"notes",            meta.notes},
  };
}

// ── calibration_payload ───────────────────────────────────────────────────

nlohmann::json calibration_payload(const Calibration& cal) {
  return {
      {"label",    cal.label},
      {"vref_mv",  cal.vref_mv},
      {"pga_gain", cal.pga_gain},
      {"adc_bits", cal.adc_bits},
  };
}

// ── quality_gate_payload ──────────────────────────────────────────────────

nlohmann::json quality_gate_payload(const QualityGate& gate) {
  auto nullable = [](const std::optional<double>& v) -> nlohmann::json {
    return v.has_value() ? nlohmann::json(v.value()) : nlohmann::json(nullptr);
  };
  return {
      {"min_duration_seconds",      gate.min_duration_seconds},
      {"min_contact_ok_percent",    gate.min_contact_ok_percent},
      {"min_r_peaks",               gate.min_r_peaks},
      {"min_hr_bpm",                gate.min_hr_bpm},
      {"max_hr_bpm",                gate.max_hr_bpm},
      {"require_qrs_clear",         gate.require_qrs_clear},
      {"max_baseline_drift_counts", nullable(gate.max_baseline_drift_counts)},
      {"max_noise_rms_counts",      nullable(gate.max_noise_rms_counts)},
      {"max_peak_to_peak_counts",   nullable(gate.max_peak_to_peak_counts)},
  };
}

// ── processing_payload ────────────────────────────────────────────────────

nlohmann::json processing_payload(const RecordingProcessingSettings& ps) {
  return {
      {"schema", ps.schema},
      {"display", {
          {"gain",                ps.gain},
          {"sweep_speed_mm_s",    ps.sweep_speed_mm_s},
          {"time_window_seconds", ps.time_window_seconds},
      }},
      {"software_filters", {
          {"bandpass_enabled", ps.bandpass_enabled},
          {"highpass_enabled", ps.highpass_enabled},
          {"highpass_hz",      ps.highpass_hz},
          {"lowpass_enabled",  ps.lowpass_enabled},
          {"lowpass_hz",       ps.lowpass_hz},
          {"notch_enabled",    ps.notch_enabled},
          {"notch_hz",         ps.notch_hz},
      }},
      {"ecg_inverted",      ps.ecg_inverted},
      {"smoothing_window",  ps.smoothing_window},
      {"processing_notes",  ps.processing_notes},
      {"sample_rate_hz",    ps.sample_rate_hz},
  };
}

// ── protocol_payload ──────────────────────────────────────────────────────

nlohmann::json protocol_payload(const TestProtocol& proto) {
  nlohmann::json steps = nlohmann::json::array();
  for (const auto& step : proto.steps) {
    steps.push_back({
        {"name",        step.name},
        {"description", step.description},
    });
  }
  return {
      {"name",                 proto.name},
      {"objective",            proto.objective},
      {"operator_instructions", proto.operator_instructions},
      {"acceptance_notes",     proto.acceptance_notes},
      {"steps",                steps},
  };
}

// ── acquisition_payload ───────────────────────────────────────────────────

nlohmann::json acquisition_payload(const AcquisitionProvenance& prov, double sample_rate_hz) {
  double sr = sample_rate_hz > 0 ? sample_rate_hz : 500.0;

  nlohmann::json channel_map = {
      {"ch1_counts",   "CH1 respiration/raw impedance"},
      {"ch2_counts",   "CH2 ECG Lead I (LA-RA)"},
      {"lead_off_bits","lead-off/contact status low nibble"},
      {"status_byte",  "ADS1x9x status byte"},
  };

  nlohmann::json csv_columns = nlohmann::json::array();
  csv_columns.push_back({
      {"name",        "timestamp"},
      {"unit",        "s"},
      {"description", "Relative seconds from recording start."},
  });
  csv_columns.push_back({
      {"name",        "sample_index"},
      {"unit",        "sample"},
      {"description", "Zero-based sample index."},
  });
  csv_columns.push_back({
      {"name",        "ch1_counts"},
      {"unit",        "live_stream_count"},
      {"description", "CH1 respiration/raw impedance"},
  });
  csv_columns.push_back({
      {"name",        "ch2_counts"},
      {"unit",        "live_stream_count"},
      {"description", "CH2 ECG Lead I (LA-RA)"},
  });
  csv_columns.push_back({
      {"name",        "board_heart_rate"},
      {"unit",        "bpm"},
      {"description", "Heart rate reported by ADS1x9x ECG-FE firmware."},
  });
  csv_columns.push_back({
      {"name",        "board_respiration_rate"},
      {"unit",        "breaths/min"},
      {"description", "Respiration rate reported by ADS1x9x ECG-FE firmware."},
  });
  csv_columns.push_back({
      {"name",        "status_byte"},
      {"unit",        "bitfield"},
      {"description", "ADS1x9x status byte from the USB stream."},
  });
  csv_columns.push_back({
      {"name",        "lead_off_bits"},
      {"unit",        "bitfield"},
      {"description", "Low-nibble lead-off/contact status bits."},
  });

  nlohmann::json completion = {
      {"status",                 "open"},
      {"ended_at",               ""},
      {"finalized_at",           ""},
      {"sample_count",           0},
      {"first_timestamp_seconds", 0.0},
      {"last_timestamp_seconds",  0.0},
      {"sample_span_seconds",     0.0},
  };

  return {
      {"schema",              prov.schema},
      {"acquisition_mode",    prov.acquisition_mode},
      {"port",                prov.port},
      {"started_at",          prov.started_at},
      {"timestamp_reference", prov.timestamp_reference},
      {"sample_rate_hz",      sr},
      {"channel_map",         channel_map},
      {"csv_columns",         csv_columns},
      {"csv_name",            prov.csv_name},
      {"csv_schema",          prov.csv_schema},
      {"completion",          completion},
      {"live_calibration",    nlohmann::json::object()},
      {"raw_adc",             nlohmann::json::object()},
  };
}

// ── build_recording_bundle ────────────────────────────────────────────

nlohmann::json build_recording_bundle(
    const std::string& csv_name, const SessionMetadata& metadata,
    const std::vector<EventMarker>& events, const Calibration& calibration,
    const AcquisitionProvenance& acquisition, const TestProtocol& protocol,
    const QualityGate& quality_gate, const RecordingProcessingSettings& processing,
    double sample_rate_hz, const std::string& created_at) {
  nlohmann::json bundle;
  bundle["schema"] = "ads1292-recording-bundle-v1";
  bundle["created_at"] = created_at;
  bundle["csv_name"] = csv_name;
  bundle["metadata"] = metadata_payload(metadata);
  bundle["calibration"] = calibration_payload(calibration);
  bundle["events"] = events_payload(events, sample_rate_hz);
  bundle["acquisition"] = acquisition_payload(acquisition, sample_rate_hz);
  bundle["protocol"] = protocol_payload(protocol);
  bundle["quality_gate"] = quality_gate_payload(quality_gate);
  bundle["processing"] = processing_payload(processing);
  return bundle;
}

}  // namespace io
}  // namespace ads1292
