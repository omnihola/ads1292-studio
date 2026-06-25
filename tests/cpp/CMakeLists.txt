# tests/cpp/CMakeLists.txt
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
  test_sha1.cpp)
target_link_libraries(ads1292_tests PRIVATE ads1292_core ads1292_io catch2 nlohmann_json)
target_compile_definitions(ads1292_tests PRIVATE
  FIXTURE_DIR="${CMAKE_SOURCE_DIR}/tests/fixtures/golden")
add_test(NAME ads1292_tests COMMAND ads1292_tests)
