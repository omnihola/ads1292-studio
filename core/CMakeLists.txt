# core/CMakeLists.txt
add_library(ads1292_core STATIC
  src/core_version.cpp
  src/model/EventMarker.cpp
  src/model/Calibration.cpp
  src/device/AdsParser.cpp)
target_include_directories(ads1292_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
