# Centralized dependency setup for SAGE C++ extensions when built via the Python superbuild.
# This file is optional: individual C++ projects can still build stand-alone by
# falling back to their local dependency scripts when SAGE_COMMON_DEPS_FILE isn't set.

cmake_minimum_required(VERSION 3.20)

# --- Configuration knobs ---------------------------------------------------
set(SAGE_PYBIND11_VERSION "2.13.0" CACHE STRING "Pinned pybind11 version for all SAGE extensions")
option(SAGE_ENABLE_GPERFTOOLS "Build extensions with gperftools/tcmalloc" OFF)
# Allow callers to provide a pre-installed gperftools root
set(SAGE_GPERFTOOLS_ROOT "" CACHE PATH "Optional root path for gperftools installation")

# --- pybind11 ---------------------------------------------------------------
find_package(pybind11 ${SAGE_PYBIND11_VERSION} EXACT CONFIG QUIET)
if(NOT pybind11_FOUND)
    include(FetchContent)
    if(NOT DEFINED pybind11_POPULATED)
        FetchContent_Declare(
            pybind11
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v${SAGE_PYBIND11_VERSION}
        )
    endif()
    FetchContent_MakeAvailable(pybind11)
endif()

# --- gperftools -------------------------------------------------------------
set(SAGE_GPERFTOOLS_LIBS "")
set(SAGE_GPERFTOOLS_INCLUDE "")
if(SAGE_ENABLE_GPERFTOOLS)
    if(SAGE_GPERFTOOLS_ROOT)
        list(APPEND CMAKE_PREFIX_PATH ${SAGE_GPERFTOOLS_ROOT})
    endif()
    find_package(gperftools QUIET)
    if(gperftools_FOUND)
        set(SAGE_GPERFTOOLS_LIBS gperftools::profiler gperftools::tcmalloc)
        if(TARGET gperftools::profiler)
            get_target_property(_tmp_include gperftools::profiler INTERFACE_INCLUDE_DIRECTORIES)
            set(SAGE_GPERFTOOLS_INCLUDE ${_tmp_include})
        endif()
    else()
        include(FetchContent)
        if(NOT TARGET gperftools::profiler)
            FetchContent_Declare(
                gperftools
                GIT_REPOSITORY https://github.com/gperftools/gperftools.git
                GIT_TAG gperftools-2.15
            )
            FetchContent_MakeAvailable(gperftools)
        endif()
        set(SAGE_GPERFTOOLS_LIBS gperftools::profiler gperftools::tcmalloc)
    endif()
endif()

# --- Common compile flags / definitions ------------------------------------
set(SAGE_COMMON_COMPILE_DEFINITIONS
    PYBIND11_INTERNALS_ID="sage_pybind11_shared"
    _GLIBCXX_USE_CXX11_ABI=1
    CACHE INTERNAL "")

set(SAGE_COMMON_COMPILE_OPTIONS
    -fvisibility=hidden
    -fvisibility-inlines-hidden
    CACHE INTERNAL "")
