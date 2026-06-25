// io/include/ads1292/io/CsvIo.h
#pragma once
#include <string>
#include <vector>
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/RawSample.h"
#include "ads1292/model/Calibration.h"

namespace ads1292 {
namespace io {

extern const std::vector<std::string> CANONICAL_HEADER;
extern const std::vector<std::string> RAW_HEADER;

void write_recording_csv(const std::string& path, const std::vector<StreamSample>& samples);
std::vector<StreamSample> read_recording_csv(const std::string& path);

void write_raw_recording_csv(const std::string& path, const std::vector<RawSample>& samples,
                             const Calibration& calibration);
std::vector<RawSample> read_raw_recording_csv(const std::string& path);

}  // namespace io
}  // namespace ads1292
