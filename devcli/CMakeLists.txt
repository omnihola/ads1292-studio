find_package(Qt6 REQUIRED COMPONENTS Core SerialPort)

add_library(ads1292_devcli_lib STATIC
  src/DevCli.cpp)

target_include_directories(ads1292_devcli_lib PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)

target_link_libraries(ads1292_devcli_lib PUBLIC
  ads1292_qt_runtime
  ads1292_core
  ads1292_io)

add_executable(ads1292_devcli
  src/main.cpp)

set_target_properties(ads1292_devcli PROPERTIES AUTOMOC ON)

target_link_libraries(ads1292_devcli PRIVATE
  ads1292_devcli_lib
  Qt6::Core)
