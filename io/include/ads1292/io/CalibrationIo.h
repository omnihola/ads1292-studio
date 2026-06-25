// io/include/ads1292/io/CalibrationIo.h
#pragma once
#include <string>
#include "ads1292/model/Calibration.h"

namespace ads1292 {
namespace io {

/// Read a JSON object from @p path and return a normalized Calibration.
/// Unknown keys are ignored; missing keys keep struct defaults.
/// Throws std::runtime_error if the file cannot be opened or the root is not a JSON object.
ads1292::Calibration read_calibration_json(const std::string& path);

/// Write @p c (after normalizing) as a pretty-printed JSON object to @p path.
/// Parent directories are created as needed.
void write_calibration_json(const std::string& path, const ads1292::Calibration& c);

/// Return the canonical calibration template (all ADS1292 defaults).
ads1292::Calibration calibration_template();

}  // namespace io
}  // namespace ads1292
