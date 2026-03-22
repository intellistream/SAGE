cmake_minimum_required(VERSION 3.20)
project(my_pkg_ext LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ─── pybind11 ─────────────────────────────────────────────────────────────────
find_package(pybind11 CONFIG REQUIRED)

# ─── Extension module ─────────────────────────────────────────────────────────
pybind11_add_module(
    _my_pkg_ext  # Python import: import my_pkg._my_pkg_ext
    csrc/bindings.cpp
    # Add more source files here:
    # csrc/core/my_module.cpp
)

target_include_directories(_my_pkg_ext PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Output the .so next to the Python package
set_target_properties(_my_pkg_ext PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src/my_pkg"
)

# ─── Optional: GoogleTest ─────────────────────────────────────────────────────
option(BUILD_TESTING "Build C++ unit tests" OFF)
if(BUILD_TESTING)
    enable_testing()
    find_package(GTest REQUIRED)
    add_subdirectory(tests/cpp)
endif()
