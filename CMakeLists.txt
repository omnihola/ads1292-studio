# CMakeLists.txt
cmake_minimum_required(VERSION 3.21)
project(ads1292_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(ADS1292_BUILD_GUI "Build the Qt GUI" ON)
option(ADS1292_BUILD_TESTS "Build C++ tests" ON)

add_subdirectory(third_party)
add_subdirectory(core)

if(ADS1292_BUILD_GUI)
  add_subdirectory(gui)
endif()

if(ADS1292_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests/cpp)
endif()
