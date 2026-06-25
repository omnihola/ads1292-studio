#pragma once
#include <optional>

namespace ads1292 {
struct StreamSample {
  double timestamp = 0.0;
  int ch1 = 0;
  int ch2 = 0;
  int board_heart_rate = 0;
  int board_respiration_rate = 0;
  int status_byte = 0;
  std::optional<int> sample_index;  // unset for stream frames (matches Python)
  int lead_off_bits() const { return status_byte & 0x0F; }
};
}  // namespace ads1292
