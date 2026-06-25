#pragma once

namespace ads1292 {
struct RawSample {
  double timestamp = 0.0;
  int sample_index = 0;
  int ch1_raw24 = 0;
  int ch2_raw24 = 0;
  int status_byte = 0;
  int lead_off_bits() const { return status_byte & 0x0F; }
};
}  // namespace ads1292
