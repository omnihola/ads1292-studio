# gui/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Widgets)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

add_executable(ads1292_gui
  src/main.cpp
  src/MainWindow.cpp
  src/MainWindow.h
  src/QCustomPlotWaveform.cpp
  resources/resources.qrc)

target_include_directories(ads1292_gui PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include)

target_link_libraries(ads1292_gui PRIVATE
  Qt6::Widgets
  qcustomplot)
