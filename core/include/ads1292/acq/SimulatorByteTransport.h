#pragma once
#include "ads1292/acq/IByteTransport.h"
namespace ads1292 { namespace acq {
class SimulatorByteTransport : public IByteTransport {
 public:
  explicit SimulatorByteTransport(std::vector<uint8_t> inbound) : inbound_(std::move(inbound)) {}
  void write(const std::vector<uint8_t>& bytes) override { last_written_ = bytes; }
  std::vector<uint8_t> read(std::size_t n) override;
  const std::vector<uint8_t>& last_written() const { return last_written_; }
 private:
  std::vector<uint8_t> inbound_;
  std::size_t pos_ = 0;
  std::vector<uint8_t> last_written_;
};
}}  // namespace ads1292::acq
