# qt_runtime/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Core SerialPort)
set(CMAKE_AUTOMOC ON)

add_library(ads1292_qt_runtime STATIC
  src/QSerialByteTransport.cpp
  src/AcquisitionWorker.cpp
  src/AdsPorts.cpp
  include/ads1292/qt/AcquisitionWorker.h
  include/ads1292/qt/QSerialByteTransport.h
  include/ads1292/qt/AdsPorts.h)

target_include_directories(ads1292_qt_runtime PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)

target_link_libraries(ads1292_qt_runtime PUBLIC
  ads1292_io
  ads1292_core
  Qt6::Core
  Qt6::SerialPort)
