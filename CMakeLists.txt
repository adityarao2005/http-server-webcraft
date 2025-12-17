cmake_minimum_required(VERSION 3.20)
project(MyHttpServer)

set(CMAKE_CXX_STANDARD 23)

# Find WebCraft package from vcpkg
find_package(WebCraft CONFIG REQUIRED)

add_executable(http_server src/main.cpp)
target_link_libraries(http_server PRIVATE WebCraft::WebCraft)