# SAGE Flow Project
cmake_minimum_required(VERSION 3.16)
project(sage_flow VERSION 1.0.0 LANGUAGES CXX)

# ============================================================================
# Global Settings
# ============================================================================
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

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

# ============================================================================
# Subdirectories
# ============================================================================
add_subdirectory(src)
add_subdirectory(tests)
# Python bindings are included via src/python/CMakeLists.txt

# ============================================================================
# Packaging
# ============================================================================
# (Packaging logic will be added here later)

# ============================================================================
# Clang-Tidy
# ============================================================================
include(cmake/ClangTidy.cmake)

# ============================================================================
# Cpplint
# ============================================================================
include(cmake/Cpplint.cmake)

# ============================================================================
# ClangFormat
# ============================================================================
option(SAGE_FLOW_ENABLE_CLANG_FORMAT "Enable clang-format integration" ON)
include(cmake/ClangFormat.cmake)

# ============================================================================
# Sanitizers
# ============================================================================
option(SAGE_FLOW_ENABLE_SANITIZERS "Enable sanitizer integration" OFF)
include(cmake/SanitizersConfig.cmake)

# ============================================================================
# Code Quality Gate
# ============================================================================
option(SAGE_FLOW_ENABLE_CODE_QUALITY_GATE "Enable code quality gate" ON)
if(SAGE_FLOW_ENABLE_CODE_QUALITY_GATE)
    include(cmake/CodeQuality.cmake)
endif()
