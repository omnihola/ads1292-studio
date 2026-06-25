#pragma once
#include <string>

namespace ads1292 {
struct Calibration {
  double vref_mv = 2420.0;
  double pga_gain = 6.0;
  int adc_bits = 24;
  std::string label = "ADS1292 default";

  Calibration normalized() const;
  double microvolts_per_count() const;
};
}  // namespace ads1292
