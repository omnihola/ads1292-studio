#include "ads1292/acq/SimulatorByteTransport.h"
namespace ads1292 { namespace acq {
std::vector<uint8_t> SimulatorByteTransport::read(std::size_t n) {
  std::vector<uint8_t> out;
  while (out.size() < n && pos_ < inbound_.size()) out.push_back(inbound_[pos_++]);
  return out;
}
}}  // namespace ads1292::acq
