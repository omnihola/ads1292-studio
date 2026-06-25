#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/EventMarker.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;
using namespace ads1292;
using namespace ads1292::io;

TEST_CASE("build_recording_bundle reproduces the full golden bundle", "[bundle]") {
  std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
  json golden; in >> golden;

  json got = build_recording_bundle(
      "rec.csv", SessionMetadata{"fixture", "p1"},
      {{0.02, "touch", "n1", 0.0}, {0.04, "motion", "n2", 0.03}},
      Calibration{}, AcquisitionProvenance{}, TestProtocol{}, QualityGate{},
      RecordingProcessingSettings{}, 500.0, "");
  REQUIRE(got == golden);
}
