cmake_minimum_required(VERSION 3.20...3.27)
project(
    ${SKBUILD_PROJECT_NAME}
    VERSION ${SKBUILD_PROJECT_VERSION}
    LANGUAGES CXX
)

# 设置 C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# 查找 Python 和 pybind11
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

# 编译选项
option(SAGE_ENABLE_GPERFTOOLS "Enable gperftools for all SAGE extensions" OFF)
set(SAGE_PYBIND11_VERSION "2.13.0" CACHE STRING "Pinned pybind11 version for SAGE extensions")
set(SAGE_GPERFTOOLS_ROOT "" CACHE PATH "Optional gperftools root directory")

# 共享依赖配置文件
set(SAGE_COMMON_DEPS_FILE
    "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/middleware/components/cmake/sage_shared_dependencies.cmake"
    CACHE FILEPATH "Common dependency configuration for SAGE extensions"
)

# 加载共享依赖（如果存在）
if(EXISTS "${SAGE_COMMON_DEPS_FILE}")
    include("${SAGE_COMMON_DEPS_FILE}")
endif()

# ============================================================================
# sage_db 扩展
# ============================================================================
set(SAGE_DB_SUBMODULE "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/middleware/components/sage_db/sageDB")

if(EXISTS "${SAGE_DB_SUBMODULE}/CMakeLists.txt")
    message(STATUS "Building sage_db extension...")
    add_subdirectory(src/sage/middleware/components/sage_db/sageDB sage_db_build)
else()
    message(WARNING "sage_db submodule not found, skipping...")
endif()

# ============================================================================
# sage_flow 扩展
# ============================================================================
set(SAGE_FLOW_SUBMODULE "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/middleware/components/sage_flow/sageFlow")

if(EXISTS "${SAGE_FLOW_SUBMODULE}/CMakeLists.txt")
    message(STATUS "Building sage_flow extension...")
    add_subdirectory(src/sage/middleware/components/sage_flow/sageFlow sage_flow_build)
else()
    message(WARNING "sage_flow submodule not found, skipping...")
endif()

# ============================================================================
# sage_tsdb 扩展
# ============================================================================
set(SAGE_TSDB_SUBMODULE "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/middleware/components/sage_tsdb/sageTSDB")

if(EXISTS "${SAGE_TSDB_SUBMODULE}/CMakeLists.txt")
    message(STATUS "Building sage_tsdb extension...")
    add_subdirectory(src/sage/middleware/components/sage_tsdb/sageTSDB sage_tsdb_build)
else()
    message(WARNING "sage_tsdb submodule not found, skipping...")
endif()

# ============================================================================
# 配置摘要
# ============================================================================
message(STATUS "")
message(STATUS "SAGE Middleware C++ Extensions Configuration")
message(STATUS "=============================================")
message(STATUS "Project: ${SKBUILD_PROJECT_NAME} v${SKBUILD_PROJECT_VERSION}")
message(STATUS "Python: ${Python_VERSION}")
message(STATUS "pybind11: ${pybind11_VERSION}")
message(STATUS "C++ Standard: C++${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "")
message(STATUS "Extensions:")
if(EXISTS "${SAGE_DB_SUBMODULE}/CMakeLists.txt")
    message(STATUS "  ✓ sage_db")
else()
    message(STATUS "  ✗ sage_db (submodule not initialized)")
endif()
if(EXISTS "${SAGE_FLOW_SUBMODULE}/CMakeLists.txt")
    message(STATUS "  ✓ sage_flow")
else()
    message(STATUS "  ✗ sage_flow (submodule not initialized)")
endif()
if(EXISTS "${SAGE_TSDB_SUBMODULE}/CMakeLists.txt")
    message(STATUS "  ✓ sage_tsdb")
else()
    message(STATUS "  ✗ sage_tsdb (submodule not initialized)")
endif()
message(STATUS "=============================================")
message(STATUS "")
