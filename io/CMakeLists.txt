# io/CMakeLists.txt
add_library(ads1292_io STATIC
  src/CsvIo.cpp
  src/Bundle.cpp
  src/RecordingBundle.cpp
  src/ReviewHtml.cpp
  src/AcquisitionEngine.cpp
  src/MetadataIo.cpp
  src/CalibrationIo.cpp
  src/EventsIo.cpp
  src/ProcessingIo.cpp
  src/ProtocolIo.cpp
  src/AcquisitionIo.cpp
  src/SessionIndexScan.cpp
  src/BatchScan.cpp
  src/QualityGateIo.cpp
  src/SidecarRepair.cpp)
target_include_directories(ads1292_io PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(ads1292_io PUBLIC ads1292_core nlohmann_json)

if(ADS1292_BUILD_HDF5)
  find_package(HDF5 REQUIRED COMPONENTS C)
  target_sources(ads1292_io PRIVATE src/H5Io.cpp)
  target_include_directories(ads1292_io PUBLIC ${HDF5_INCLUDE_DIRS})
  target_link_libraries(ads1292_io PUBLIC ${HDF5_C_LIBRARIES})
  target_compile_definitions(ads1292_io PUBLIC ADS1292_HAVE_HDF5=1)
endif()
