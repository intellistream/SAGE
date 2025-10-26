cmake_minimum_required(VERSION 3.20)
project(sage_middleware_superbuild LANGUAGES CXX)

option(SAGE_ENABLE_GPERFTOOLS "Enable gperftools for all SAGE extensions" OFF)
set(SAGE_PYBIND11_VERSION "2.13.0" CACHE STRING "Pinned pybind11 version for SAGE extensions")
set(SAGE_GPERFTOOLS_ROOT "" CACHE PATH "Optional gperftools root directory")

set(SAGE_COMMON_DEPS_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/middleware/components/cmake/sage_shared_dependencies.cmake"
    CACHE FILEPATH "Common dependency configuration for SAGE extensions"
)

add_subdirectory(src/sage/middleware/components/sage_db/sageDB)
add_subdirectory(src/sage/middleware/components/sage_flow/sageFlow)
