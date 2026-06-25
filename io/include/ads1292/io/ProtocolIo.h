#pragma once
// io/include/ads1292/io/ProtocolIo.h
// JSON read/write/template for TestProtocol and ProtocolStep.
// No Qt. Uses nlohmann/json internally (not exposed in this header).

#include <string>
#include "ads1292/model/TestProtocol.h"

namespace ads1292 {
namespace io {

/// Read a protocol JSON file from @p path and return a normalized TestProtocol.
/// Unknown keys are ignored; missing keys keep struct defaults.
/// Throws std::runtime_error if the file cannot be opened or the root is not a JSON object.
ads1292::TestProtocol read_protocol_json(const std::string& path);

/// Write @p p (after normalizing) as a pretty-printed JSON object to @p path.
/// Parent directories are created as needed.
void write_protocol_json(const std::string& path, const ads1292::TestProtocol& p);

/// Return the canonical MOTAC ECG validation protocol template.
/// Matches Python protocol_template() exactly.
ads1292::TestProtocol protocol_template();

}  // namespace io
}  // namespace ads1292
