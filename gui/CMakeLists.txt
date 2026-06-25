# gui/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Widgets)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

add_executable(ads1292_gui
  src/main.cpp
  src/MainWindow.cpp
  src/MainWindow.h
  resources/resources.qrc)
target_link_libraries(ads1292_gui PRIVATE Qt6::Widgets)
