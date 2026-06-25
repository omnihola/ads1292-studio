#include "ads1292/acq/AdsFraming.h"
namespace ads1292 { namespace acq {
namespace {
std::size_t payload_len(uint8_t type) {
  switch (type) { case 0x93: return 61; case 0x92: case 0x99: return 5; case 0x94: return 51; default: return 1; }
}
bool read_one(IByteTransport& t, uint8_t& out) { auto b = t.read(1); if (b.empty()) return false; out = b[0]; return true; }
}  // namespace

std::vector<uint8_t> build_cmd(uint8_t cmd, uint8_t p0, uint8_t p1) {
  return {kStart, cmd, p0, p1, kEnd, kEnd, 0x0A};
}

Frame read_frame(IByteTransport& transport) {
  Frame f;
  uint8_t byte = 0;
  // scan to START
  for (;;) { if (!read_one(transport, byte)) return f; if (byte == kStart) break; }
  if (!read_one(transport, f.type)) return f;
  std::size_t need = payload_len(f.type);
  std::vector<uint8_t> payload = transport.read(need);
  if (payload.size() != need) return f;  // ok stays false on a short read
  f.payload = std::move(payload);
  f.ok = true;
  return f;
}
}}  // namespace ads1292::acq
