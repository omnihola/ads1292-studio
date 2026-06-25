# gui/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Widgets)

# ---------------------------------------------------------------------------
# ads1292_gui_lib — static library containing all GUI widget sources.
# Both the ads1292_gui executable and the test suite link this target so
# that widget sources are compiled exactly once.
# ---------------------------------------------------------------------------
add_library(ads1292_gui_lib STATIC
  src/MainWindow.cpp
  src/MainWindow.h
  src/QCustomPlotWaveform.cpp
  resources/resources.qrc)

set_target_properties(ads1292_gui_lib PROPERTIES
  AUTOMOC ON
  AUTORCC ON)

# PUBLIC so that consumers (exe + tests) inherit the include paths.
# Expose both the installed public headers (include/) and the src/ directory
# so that MainWindow.h (a private-but-linkable header) is also visible.
target_include_directories(ads1292_gui_lib PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)

target_link_libraries(ads1292_gui_lib PUBLIC
  ads1292_io
  ads1292_core
  qcustomplot
  Qt6::Widgets)

# ---------------------------------------------------------------------------
# ads1292_gui — thin executable; all logic lives in ads1292_gui_lib.
# ---------------------------------------------------------------------------
add_executable(ads1292_gui src/main.cpp)

target_link_libraries(ads1292_gui PRIVATE ads1292_gui_lib)
