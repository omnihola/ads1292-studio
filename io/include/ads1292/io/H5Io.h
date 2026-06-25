#pragma once
#include <string>
#include <vector>
#include "ads1292/model/StreamSample.h"

namespace ads1292 {
namespace io {

bool h5_smoke_roundtrip(const std::string& path);

struct H5Attrs {
  std::string schema;
  std::string created_at;
  std::string csv_name;
  std::string sample_rate_hz;
  std::string sample_count;
};

struct H5Recording {
  std::vector<StreamSample> samples;
  std::string bundle_json;
  H5Attrs attrs;
};

H5Recording read_recording_h5(const std::string& path);

std::string dataset_float64_sha256(const std::vector<double>& values);

}  // namespace io
}  // namespace ads1292
