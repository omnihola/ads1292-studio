# gui/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Widgets)

# ---------------------------------------------------------------------------
# ads1292_gui_lib — static library containing all GUI widget sources.
# Both the ads1292_gui executable and the test suite link this target so
# that widget sources are compiled exactly once.
# ---------------------------------------------------------------------------
add_library(ads1292_gui_lib STATIC
  src/MainWindow.cpp
  src/QCustomPlotWaveform.cpp
  src/QCustomPlotXY.cpp
  src/LiveScope.cpp
  src/StatusPanel.cpp
  src/EventConsole.cpp
  src/PqrstPanel.cpp
  src/SpectrumPanel.cpp
  src/QualityInfoPanel.cpp
  src/ReviewEventLogPanel.cpp
  src/ReportExport.cpp
  resources/resources.qrc)

set_target_properties(ads1292_gui_lib PROPERTIES
  AUTOMOC ON
  AUTORCC ON)

# PUBLIC so that consumers (exe + tests) inherit the include paths.
# MainWindow.h is now in include/ads1292/gui/ (public header location).
target_include_directories(ads1292_gui_lib PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)

target_link_libraries(ads1292_gui_lib PUBLIC
  ads1292_qt_runtime
  ads1292_io
  ads1292_core
  qcustomplot
  Qt6::Widgets)

# ---------------------------------------------------------------------------
# ads1292_gui — thin executable; all logic lives in ads1292_gui_lib.
# ---------------------------------------------------------------------------
add_executable(ads1292_gui src/main.cpp)

target_link_libraries(ads1292_gui PRIVATE ads1292_gui_lib)
