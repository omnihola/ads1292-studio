// io/include/ads1292/io/MetadataIo.h
#pragma once
#include <string>
#include "ads1292/model/SessionMetadata.h"

namespace ads1292 {
namespace io {

/// Read a JSON object from @p path and return a normalized SessionMetadata.
/// Unknown keys are ignored; missing keys keep struct defaults.
/// Throws std::runtime_error if the file cannot be opened or the root is not a JSON object.
ads1292::SessionMetadata read_metadata_json(const std::string& path);

/// Write @p m (after normalizing) as a pretty-printed JSON object to @p path.
/// Parent directories are created as needed.
void write_metadata_json(const std::string& path, const ads1292::SessionMetadata& m);

/// Return the canonical metadata template with recommended placeholder values.
ads1292::SessionMetadata metadata_template();

}  // namespace io
}  // namespace ads1292
