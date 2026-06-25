# cli/CMakeLists.txt
# Qt-free CLI library + binary.
# Links ads1292_core + ads1292_io only (no Qt).

add_library(ads1292_cli_lib STATIC src/Cli.cpp)
target_include_directories(ads1292_cli_lib PUBLIC include)
target_link_libraries(ads1292_cli_lib PUBLIC ads1292_core ads1292_io)

add_executable(ads1292_cli src/main.cpp)
target_link_libraries(ads1292_cli PRIVATE ads1292_cli_lib)
