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
# sage_db - Vector Database C++ Library + Python Bindings
# ============================================================================
set(SAGE_DB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/middleware/components/sage_db")
set(SAGE_DB_SUBMODULE "${SAGE_DB_DIR}/sageDB")

if(EXISTS "${SAGE_DB_SUBMODULE}/CMakeLists.txt")
    message(STATUS "Adding sage_db submodule...")

    # 让子模块保持独立完整：可以自己编译、测试、构建 Python bindings
    # Middleware 只是引用子模块已经构建好的 Python bindings
    # 但在 middleware 构建时跳过测试以加快构建速度
    set(BUILD_TESTS OFF CACHE BOOL "Skip tests in middleware build" FORCE)
    set(BUILD_PYTHON_BINDINGS ON CACHE BOOL "Enable Python bindings in submodule" FORCE)
    add_subdirectory(${SAGE_DB_SUBMODULE} sage_db_build)

    message(STATUS "  ✓ sage_db configured (with independent Python bindings)")
else()
    message(WARNING "sage_db submodule not found at ${SAGE_DB_SUBMODULE}")
endif()

# ============================================================================
# sage_flow - Stream Processing C++ Library + Python Bindings
# ============================================================================
set(SAGE_FLOW_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/middleware/components/sage_flow")
set(SAGE_FLOW_SUBMODULE "${SAGE_FLOW_DIR}/sageFlow")

if(EXISTS "${SAGE_FLOW_SUBMODULE}/CMakeLists.txt")
    message(STATUS "Adding sage_flow submodule...")

    # 让子模块保持独立完整：可以自己编译、测试、构建 Python bindings
    # 但在 middleware 构建时跳过测试以避免循环依赖问题
    set(BUILD_TESTS OFF CACHE BOOL "Skip tests to avoid circular dependencies" FORCE)
    set(BUILD_PYTHON_BINDINGS ON CACHE BOOL "Enable Python bindings in submodule" FORCE)
    add_subdirectory(${SAGE_FLOW_SUBMODULE} sage_flow_build)

    message(STATUS "  ✓ sage_flow configured (with independent Python bindings)")
else()
    message(WARNING "sage_flow submodule not found at ${SAGE_FLOW_SUBMODULE}")
endif()

# ============================================================================
# sage_tsdb - Time Series Database C++ Library + Python Bindings
# ============================================================================
set(SAGE_TSDB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/middleware/components/sage_tsdb")
set(SAGE_TSDB_SUBMODULE "${SAGE_TSDB_DIR}/sageTSDB")

if(EXISTS "${SAGE_TSDB_SUBMODULE}/CMakeLists.txt")
    message(STATUS "Adding sage_tsdb submodule...")

    # 让子模块保持独立完整：可以自己编译、测试、构建 Python bindings
    # 但在 middleware 构建时跳过测试以加快构建速度
    set(BUILD_TESTS OFF CACHE BOOL "Skip tests in middleware build" FORCE)
    set(BUILD_PYTHON_BINDINGS ON CACHE BOOL "Enable Python bindings in submodule" FORCE)
    add_subdirectory(${SAGE_TSDB_SUBMODULE} sage_tsdb_build)

    message(STATUS "  ✓ sage_tsdb configured (with independent Python bindings)")
else()
    message(WARNING "sage_tsdb submodule not found at ${SAGE_TSDB_SUBMODULE}")
endif()

# ============================================================================
# 配置摘要
# ============================================================================
message(STATUS "")
message(STATUS "SAGE Middleware C++ Extensions - Build Summary")
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
message(STATUS "Extensions:")
if(TARGET _sage_db)
    message(STATUS "  ✓ sage_db")
else()
    message(STATUS "  ✗ sage_db (not configured)")
endif()
if(TARGET _sage_flow)
    message(STATUS "  ✓ sage_flow")
else()
    message(STATUS "  ✗ sage_flow (not configured)")
endif()
if(TARGET _sage_tsdb)
    message(STATUS "  ✓ sage_tsdb")
else()
    message(STATUS "  ✗ sage_tsdb (not configured)")
endif()
message(STATUS "===============================================")
message(STATUS "")
