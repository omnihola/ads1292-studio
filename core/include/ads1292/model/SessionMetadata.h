#pragma once
#include <string>

namespace ads1292 {

struct SessionMetadata {
  std::string session_id      = "";
  std::string subject_id      = "anonymous";
  std::string electrode       = "";
  std::string montage         = "RA/LA/RL torso";
  std::string operator_       = "";   // JSON key is "operator" (C++ keyword avoided)
  std::string notes           = "";
  std::string acquisition_mode = "live_stream";

  SessionMetadata normalized() const;
};

}  // namespace ads1292
