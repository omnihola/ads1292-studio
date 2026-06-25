#pragma once
#include <cstdint>
#include <vector>
namespace ads1292 { namespace acq {
class IByteTransport {
 public:
  virtual ~IByteTransport() = default;
  virtual void write(const std::vector<uint8_t>& bytes) = 0;
  virtual std::vector<uint8_t> read(std::size_t n) = 0;  // up to n bytes; fewer at end-of-input
};
}}  // namespace ads1292::acq
