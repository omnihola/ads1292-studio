#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/model/Calibration.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;
using namespace ads1292;
using namespace ads1292::io;

namespace {
json golden() {
  std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
  json j; in >> j; return j;
}
}  // namespace

TEST_CASE("each bundle sub-object reproduces its golden section", "[bundle]") {
  json g = golden();
  REQUIRE(metadata_payload(SessionMetadata{"fixture", "p1"}) == g.at("metadata"));
  REQUIRE(calibration_payload(Calibration{}) == g.at("calibration"));
  REQUIRE(quality_gate_payload(QualityGate{}) == g.at("quality_gate"));
  REQUIRE(processing_payload(RecordingProcessingSettings{}) == g.at("processing"));
  REQUIRE(protocol_payload(TestProtocol{}) == g.at("protocol"));
  REQUIRE(acquisition_payload(AcquisitionProvenance{}, 500.0) == g.at("acquisition"));
}
