#include "ads1292/acq/AdsProtocolDevice.h"
#include "ads1292/acq/AdsFraming.h"
#include "ads1292/device/AdsParser.h"

namespace ads1292 { namespace acq {

AdsProtocolDevice::AdsProtocolDevice(IByteTransport& transport, double sample_rate_hz)
    : t_(transport), sample_rate_hz_(sample_rate_hz) {}

void AdsProtocolDevice::start_stream() {
  t_.write(build_cmd(0x93, 0, 0));
  streaming_ = true;
  stream_index_ = 0;
  t0_ = 0.0;
}

void AdsProtocolDevice::stop_stream() {
  t_.write(build_cmd(0x93, 0, 0));
  streaming_ = false;
}

std::vector<ads1292::StreamSample> AdsProtocolDevice::read_stream_batch() {
  Frame f = read_frame(t_);
  if (!f.ok || f.type != 0x93 || f.payload.size() < 61) {
    return {};
  }
  auto s = parse_stream_payload(f.payload, t0_, sample_rate_hz_, stream_index_);
  stream_index_ += static_cast<int>(s.size());
  return s;
}

std::vector<ads1292::RawSample> AdsProtocolDevice::acquire_raw(int count) {
  if (count <= 0 || count % 8 != 0) {
    throw AdsParseError("acquire_raw: count must be positive and a multiple of 8");
  }

  t_.write(build_cmd(0x94, static_cast<uint8_t>((count >> 8) & 0xFF),
                     static_cast<uint8_t>(count & 0xFF)));

  Frame ack = read_frame(t_);
  if (!ack.ok || ack.type != 0x94 || ack.payload.size() < 2) {
    throw AdsParseError("acquire ACK mismatch");
  }
  int ack_count = (static_cast<int>(ack.payload[0]) << 8) | static_cast<int>(ack.payload[1]);
  if (ack_count != count) {
    throw AdsParseError("acquire ACK mismatch");
  }

  std::vector<ads1292::RawSample> result;
  int collected = 0;
  while (collected < count) {
    Frame f = read_frame(t_);
    if (!f.ok) {
      throw AdsParseError("acquire underrun");
    }
    if (f.type != 0x94) {
      continue;
    }
    auto batch = parse_acquire_payload(f.payload, 0.0, sample_rate_hz_, collected);
    for (auto& s : batch) {
      result.push_back(std::move(s));
    }
    collected += static_cast<int>(batch.size());
  }

  result.resize(static_cast<std::size_t>(count));
  return result;
}

std::string AdsProtocolDevice::query_firmware(int max_frames) {
  t_.write(build_cmd(0x99, 0, 0));
  std::string last_frame_detail;
  for (int i = 0; i < max_frames; ++i) {
    Frame f = read_frame(t_);
    if (!f.ok) {
      break;  // end of input or short read — no more frames
    }
    if (f.type == 0x99 && f.payload.size() >= 2) {
      return std::to_string(static_cast<unsigned>(f.payload[0])) + "." +
             std::to_string(static_cast<unsigned>(f.payload[1]));
    }
    // Non-0x99 frame — record for the fallback message and keep looping
    last_frame_detail = "0x" + [&] {
      char buf[3];
      std::snprintf(buf, sizeof(buf), "%02X", static_cast<unsigned>(f.type));
      return std::string(buf);
    }();
  }
  if (last_frame_detail.empty()) {
    return "no firmware response";
  }
  return "no firmware response; last frame " + last_frame_detail;
}

}}  // namespace ads1292::acq
