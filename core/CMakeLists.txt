# core/CMakeLists.txt
add_library(ads1292_core STATIC
  src/core_version.cpp
  src/model/EventMarker.cpp
  src/model/Calibration.cpp
  src/device/AdsParser.cpp
  src/crypto/Sha1.cpp
  src/crypto/Sha256.cpp
  src/event/EventId.cpp
  src/acq/SimulatorByteTransport.cpp
  src/acq/AdsFraming.cpp
  src/acq/AdsProtocolDevice.cpp
  src/acq/SimulatorDeviceSource.cpp
  src/view/RollingTrace.cpp)
target_include_directories(ads1292_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(ads1292_core PUBLIC picosha2)
