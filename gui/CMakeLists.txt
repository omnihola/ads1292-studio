# gui/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Widgets)

# ---------------------------------------------------------------------------
# ads1292_gui_lib — static library containing all GUI widget sources.
# Both the ads1292_gui executable and the test suite link this target so
# that widget sources are compiled exactly once.
# ---------------------------------------------------------------------------
add_library(ads1292_gui_lib STATIC
  # Explicit header listing so AUTOMOC processes Q_OBJECT in the canonical
  # include-tree header (not just the adjacent-to-src scanning heuristic).
  include/ads1292/gui/MainWindow.h
  src/MainWindow.cpp
  src/RecordingPaths.cpp
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
# On Apple, build as a MACOSX_BUNDLE (.app) with a templated Info.plist.
# On other platforms, keep a plain executable.
# ---------------------------------------------------------------------------
if(APPLE)
  # Make MACOSX_BUNDLE_EXECUTABLE_NAME available as a CMake variable so that
  # the ${MACOSX_BUNDLE_EXECUTABLE_NAME} placeholder in Info.plist.in is
  # substituted correctly during the configure/generate step.
  set(MACOSX_BUNDLE_EXECUTABLE_NAME "ads1292_gui")

  add_executable(ads1292_gui MACOSX_BUNDLE src/main.cpp)

  set_target_properties(ads1292_gui PROPERTIES
    MACOSX_BUNDLE_INFO_PLIST         "${CMAKE_CURRENT_SOURCE_DIR}/Info.plist.in"
    MACOSX_BUNDLE_BUNDLE_NAME        "ADS1292 Studio"
    MACOSX_BUNDLE_GUI_IDENTIFIER     "com.ads1292studio.gui"
    MACOSX_BUNDLE_BUNDLE_VERSION     "1.0.0"
    MACOSX_BUNDLE_SHORT_VERSION_STRING "1.0.0"
    MACOSX_BUNDLE_EXECUTABLE_NAME    "ads1292_gui")
else()
  add_executable(ads1292_gui src/main.cpp)
endif()

target_link_libraries(ads1292_gui PRIVATE ads1292_gui_lib)
