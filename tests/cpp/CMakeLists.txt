# tests/cpp/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Widgets)

add_executable(ads1292_tests
  test_main.cpp
  test_smoke.cpp
  test_event_marker.cpp
  test_byte_decode.cpp
  FixtureLoader.cpp
  test_fixture_loader.cpp
  test_device_parser_stream.cpp
  test_device_parser_acquire.cpp
  test_calibration.cpp
  test_csv_live.cpp
  test_csv_raw.cpp
  test_sha1.cpp
  test_sha256.cpp
  test_event_id.cpp
  test_bundle_events.cpp
  test_bundle_sections.cpp
  test_bundle_assembly.cpp
  test_ads_protocol.cpp
  test_acquisition_engine.cpp
  test_acq_worker_smoke.cpp
  test_rolling_trace.cpp
  test_event_log.cpp
  test_gui_smoke.cpp
  ${CMAKE_SOURCE_DIR}/gui/src/QCustomPlotWaveform.cpp)

set_target_properties(ads1292_tests PROPERTIES AUTOMOC ON)

if(ADS1292_BUILD_HDF5)
  target_sources(ads1292_tests PRIVATE test_h5_io.cpp test_h5_read.cpp test_h5_write.cpp)
endif()

target_include_directories(ads1292_tests PRIVATE
  ${CMAKE_SOURCE_DIR}/gui/include)

target_link_libraries(ads1292_tests PRIVATE
  ads1292_core
  ads1292_io
  ads1292_qt_runtime
  catch2
  nlohmann_json
  qcustomplot
  Qt6::Widgets)
target_compile_definitions(ads1292_tests PRIVATE
  FIXTURE_DIR="${CMAKE_SOURCE_DIR}/tests/fixtures/golden")
add_test(NAME ads1292_tests COMMAND ads1292_tests)
