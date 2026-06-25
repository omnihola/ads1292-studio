#pragma once
#include <cstdint>
#include <vector>
#include "ads1292/acq/IByteTransport.h"
namespace ads1292 { namespace acq {
constexpr uint8_t kStart = 0x02, kEnd = 0x03;
std::vector<uint8_t> build_cmd(uint8_t cmd, uint8_t p0, uint8_t p1);
struct Frame { uint8_t type = 0; std::vector<uint8_t> payload; bool ok = false; };
Frame read_frame(IByteTransport& transport);
}}  // namespace ads1292::acq
