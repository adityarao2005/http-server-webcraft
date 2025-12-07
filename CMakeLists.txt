cmake_minimum_required(VERSION 3.20)
project(MyHttpServer)

set(CMAKE_CXX_STANDARD 23)

# Point to vcpkg toolchain
set(CMAKE_TOOLCHAIN_FILE "${CMAKE_CURRENT_SOURCE_DIR}/vcpkg/scripts/buildsystems/vcpkg.cmake"
    CACHE STRING "Vcpkg toolchain file")

# Disable WebCraft tests
option(BUILD_TESTING "Build tests" OFF)
set(WEBCRAFT_BUILD_TESTS OFF CACHE BOOL "" FORCE)

# Add WebCraft
add_subdirectory(external/WebCraft EXCLUDE_FROM_ALL)

add_executable(http_server src/main.cpp)
target_link_libraries(http_server PRIVATE WebCraft)