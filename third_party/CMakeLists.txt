# third_party/CMakeLists.txt
add_library(catch2 INTERFACE)
target_include_directories(catch2 INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/catch2)

add_library(nlohmann_json INTERFACE)
target_include_directories(nlohmann_json INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})

add_library(picosha2 INTERFACE)
target_include_directories(picosha2 INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/picosha2)
