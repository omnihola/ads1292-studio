#pragma once
#include <cstdint>
#include <vector>
#include "ads1292/acq/IByteTransport.h"
namespace ads1292 { namespace acq {
constexpr uint8_t kStart = 0x02, kEnd = 0x03;
std::vector<uint8_t> build_cmd(uint8_t cmd, uint8_t p0, uint8_t p1);
struct Frame { uint8_t type = 0; std::vector<uint8_t> payload; bool ok = false; };
Frame read_frame(IByteTransport& transport);

/// Variable-length frame reader: scans to kStart, reads type, then appends
/// bytes one at a time until kEnd (0x03) is seen — payload does NOT include
/// the END byte.  Returns ok=true when END is seen; ok=false if the transport
/// runs out of bytes before END.  Used for the acquire ACK which is a short
/// variable-length response, not a fixed-size data frame.
Frame read_frame_until_end(IByteTransport& transport);
}}  // namespace ads1292::acq
