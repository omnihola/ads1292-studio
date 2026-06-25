# third_party/CMakeLists.txt
add_library(catch2 INTERFACE)
target_include_directories(catch2 INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/catch2)

add_library(nlohmann_json INTERFACE)
target_include_directories(nlohmann_json INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})

add_library(picosha2 INTERFACE)
target_include_directories(picosha2 INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/picosha2)

find_package(Qt6 REQUIRED COMPONENTS Widgets PrintSupport)
add_library(qcustomplot STATIC qcustomplot/qcustomplot.cpp)
target_include_directories(qcustomplot PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/qcustomplot)
target_link_libraries(qcustomplot PUBLIC Qt6::Widgets Qt6::PrintSupport)
set_target_properties(qcustomplot PROPERTIES AUTOMOC ON)
