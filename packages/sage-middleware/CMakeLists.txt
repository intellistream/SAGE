cmake_minimum_required(VERSION 3.20...3.27)
project(
    ${SKBUILD_PROJECT_NAME}
    VERSION ${SKBUILD_PROJECT_VERSION}
    LANGUAGES CXX C
)

# ============================================================================
# 全局编译设置
# ============================================================================
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# 编译选项
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -fPIC")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")

# ============================================================================
# 查找依赖
# ============================================================================
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)
find_package(Threads REQUIRED)
find_package(OpenMP)

message(STATUS "")
message(STATUS "=== SAGE Middleware Build Configuration ===")
message(STATUS "Python: ${Python_VERSION}")
message(STATUS "pybind11: ${pybind11_VERSION}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
if(OpenMP_CXX_FOUND)
    message(STATUS "OpenMP: ${OpenMP_CXX_VERSION}")
endif()
message(STATUS "==========================================")
message(STATUS "")

# ============================================================================
# NOTE: sage_db, sage_flow, sage_tsdb are now independent PyPI packages
# ============================================================================
# These components have been migrated from submodules to PyPI packages:
# - sage_db   → isagedb (pip install isagedb)
# - sage_flow → isage-flow (pip install isage-flow)
# - sage_tsdb → isage-tsdb (pip install isage-tsdb)
#
# No C++ compilation needed for sage-middleware package.
# The Python wrappers in sage.middleware.components.* will import from these packages.
# ============================================================================

message(STATUS "")
message(STATUS "=== SAGE Middleware Components ===")
message(STATUS "All C++ extensions are now independent PyPI packages:")
message(STATUS "  • sage_db   → isagedb (https://pypi.org/project/isagedb/)")
message(STATUS "  • sage_flow → isage-flow (https://pypi.org/project/isage-flow/)")
message(STATUS "  • sage_tsdb → isage-tsdb (https://pypi.org/project/isage-tsdb/)")
message(STATUS "")
message(STATUS "Install with: pip install isagedb isage-flow isage-tsdb")
message(STATUS "==================================")
message(STATUS "")

# ============================================================================
# 配置摘要
# ============================================================================
message(STATUS "")
message(STATUS "SAGE Middleware - Build Summary")
message(STATUS "===============================================")
message(STATUS "Project: ${SKBUILD_PROJECT_NAME} v${SKBUILD_PROJECT_VERSION}")
message(STATUS "Python: ${Python_VERSION}")
message(STATUS "pybind11: ${pybind11_VERSION}")
message(STATUS "C++ Standard: C++${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "")
message(STATUS "🔍 SKBUILD Variables:")
message(STATUS "  SKBUILD_STATE: ${SKBUILD_STATE}")
message(STATUS "  SKBUILD_PLATLIB_DIR: ${SKBUILD_PLATLIB_DIR}")
message(STATUS "")
message(STATUS "📦 C++ Extensions Status:")
message(STATUS "  All C++ components are now independent PyPI packages.")
message(STATUS "  No compilation needed for sage-middleware.")
message(STATUS "")
message(STATUS "  Install dependencies with:")
message(STATUS "    pip install isagedb isage-flow isage-tsdb")
message(STATUS "===============================================")
message(STATUS "")
