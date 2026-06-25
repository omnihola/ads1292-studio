// core/src/model/Calibration.cpp
#include "ads1292/model/Calibration.h"
#include <cctype>
#include <cmath>

namespace ads1292 {
namespace {
std::string strip(const std::string& s) {
  size_t b = 0, e = s.size();
  while (b < e && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
  while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) --e;
  return s.substr(b, e - b);
}
}  // namespace

Calibration Calibration::normalized() const {
  Calibration out;
  out.vref_mv = vref_mv > 0 ? vref_mv : 2420.0;
  out.pga_gain = pga_gain > 0 ? pga_gain : 6.0;
  out.adc_bits = adc_bits >= 2 ? adc_bits : 24;
  std::string trimmed = strip(label);
  out.label = trimmed.empty() ? "ADS1292 default" : trimmed;
  return out;
}

double Calibration::microvolts_per_count() const {
  Calibration n = normalized();
  double full_scale_counts = std::pow(2.0, static_cast<double>(n.adc_bits - 1));
  return n.vref_mv * 1000.0 / (n.pga_gain * full_scale_counts);
}
}  // namespace ads1292
