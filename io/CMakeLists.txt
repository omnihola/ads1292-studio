# io/CMakeLists.txt
add_library(ads1292_io STATIC
  src/CsvIo.cpp
  src/Bundle.cpp)
target_include_directories(ads1292_io PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(ads1292_io PUBLIC ads1292_core nlohmann_json)
