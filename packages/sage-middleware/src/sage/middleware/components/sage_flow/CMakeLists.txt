# SAGE Flow Project
cmake_minimum_required(VERSION 3.28)
project(sage_flow VERSION 1.0.0 LANGUAGES CXX)

# Switch to Clang++ compiler
set(CMAKE_CXX_COMPILER "clang++")

set(CMAKE_BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR})

# ============================================================================
# Global Settings
# ============================================================================

# Use Ninja generator
set(CMAKE_GENERATOR "Ninja")
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Warning flags for clean compilation
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC -Wall -Wextra -Wpedantic")

# Multi-platform threading support
find_package(Threads REQUIRED)

# Python and pybind11 for bindings
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module NumPy)
find_package(pybind11 2.10 REQUIRED)

# Default build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# ============================================================================
# Compiler and Linker Settings
# ============================================================================
# Use static linking for libstdc++ to avoid GLIBC version issues
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static-libstdc++ -static-libgcc")
set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -static-libstdc++ -static-libgcc")

# Find Python and pybind11 for bindings
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module NumPy)
find_package(pybind11 REQUIRED)

option(ENABLE_DEV_TOOLS "Enable development tools integration" OFF)

# ============================================================================
# Subdirectories
# ============================================================================

# Include directories for all C++ components
include_directories(include)
option(BUILD_TESTING "Build the testing tree." OFF)
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()
add_subdirectory(src)
add_subdirectory(bindings/python)
# Python bindings are included via src/python/CMakeLists.txt

# ============================================================================
# Packaging
# ============================================================================
# (Packaging logic will be added here later)

# Install Python bindings
install(TARGETS sageflow LIBRARY DESTINATION ${Python3_SITELIB}/sageflow)

# ============================================================================
# Clang-Tidy
# ============================================================================
if(ENABLE_DEV_TOOLS)
    include(cmake/ClangTidy.cmake)
endif()

# ============================================================================
# Cpplint
# ============================================================================
if(ENABLE_DEV_TOOLS)
    include(cmake/Cpplint.cmake)
endif()

# ============================================================================
# ClangFormat
# ============================================================================
if(ENABLE_DEV_TOOLS)
    option(SAGE_FLOW_ENABLE_CLANG_FORMAT "Enable clang-format integration" ON)
    include(cmake/ClangFormat.cmake)
endif()

# ============================================================================
# Sanitizers
# ============================================================================
if(ENABLE_DEV_TOOLS)
    option(SAGE_FLOW_ENABLE_SANITIZERS "Enable sanitizer integration" OFF)
    include(cmake/SanitizersConfig.cmake)
endif()

# ============================================================================
# Code Quality Gate
# ============================================================================
if(ENABLE_DEV_TOOLS)
    option(SAGE_FLOW_ENABLE_CODE_QUALITY_GATE "Enable code quality gate" ON)
    if(SAGE_FLOW_ENABLE_CODE_QUALITY_GATE)
        include(cmake/CodeQuality.cmake)
    endif()
endif()
