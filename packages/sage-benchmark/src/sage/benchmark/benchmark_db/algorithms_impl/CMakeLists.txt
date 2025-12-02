# CMakeLists.txt for algorithms_impl - 编译 PyCANDYAlgo 模块
# 基于 SAGE-DB-Bench 主项目简化而来 (CPU only)

cmake_minimum_required(VERSION 3.14)
project(PyCANDYAlgo_Build LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# 设置路径
set(ALGORITHMS_IMPL_DIR ${CMAKE_CURRENT_SOURCE_DIR})
set(FAISS_DIR ${ALGORITHMS_IMPL_DIR}/faiss)
set(DISKANN_DIR ${ALGORITHMS_IMPL_DIR}/DiskANN)
set(PUCK_DIR ${ALGORITHMS_IMPL_DIR}/puck)
set(SPTAG_DIR ${ALGORITHMS_IMPL_DIR}/SPTAG)
set(PYBIND11_DIR ${ALGORITHMS_IMPL_DIR}/pybind11)
set(CANDY_DIR ${ALGORITHMS_IMPL_DIR}/candy)

# 查找依赖
find_package(Python3 REQUIRED COMPONENTS Development)
find_package(Torch REQUIRED)
find_package(gflags REQUIRED)

# 配置选项 - 禁用 PAPI 和 Ray (CPU only build)
set(CANDY_PAPI 0)
set(CANDY_RAY 0)
set(ENABLE_RAY OFF)

# 生成配置头文件
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/include/papi_config.h.in"
    "${CMAKE_CURRENT_BINARY_DIR}/include/papi_config.h"
)

# 收集 CANDY 源文件
file(GLOB_RECURSE CANDY_SOURCES
    "${CANDY_DIR}/*.cpp"
)

# 排除需要 Ray 的文件和重复的 Worker 文件 (因为 ENABLE_RAY=OFF)
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*DistributedPartitionIndex.*")
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*ConcurrentIndexWorker.*")
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*CongestionDropIndexWorker.*")
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*CongestionDropIndex.*")
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*BufferedCongestionDropIndex.*")
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*FlatAMMIPIndex.*")
# 排除所有 main.cpp 文件 (可执行文件，不应该编译到库中)
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*/main\\.cpp$")
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*FlatAMMIPObjIndex.*")
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*HNSWNaiveIndex.*")
list(FILTER CANDY_SOURCES EXCLUDE REGEX ".*HNSWNaive/HNSW.*")

# 包含目录
# 将 candy 目录作为 CANDY 包含路径，这样可以使用 <CANDY/xxx.h>
include_directories(
    ${ALGORITHMS_IMPL_DIR}
    ${ALGORITHMS_IMPL_DIR}/include
    ${CANDY_DIR}
    ${CANDY_DIR}/Utils
    ${CANDY_DIR}/DataLoader
    ${CMAKE_CURRENT_BINARY_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
    ${DISKANN_DIR}/include
    ${DISKANN_DIR}/python/include
    ${PUCK_DIR}
    ${SPTAG_DIR}/AnnService
    ${TORCH_INCLUDE_DIRS}
    ${Python3_INCLUDE_DIRS}
)

# 添加预处理器定义，将 CANDY 映射到 candy 目录
add_compile_definitions(CANDY_INCLUDE_DIR="${CANDY_DIR}")

# 编译 Faiss
message(STATUS "Building Faiss...")
add_subdirectory(${FAISS_DIR} faiss_build)

# 编译 DiskANN
message(STATUS "Building DiskANN...")
set(DISKANN_BUILD_PYTHON ON CACHE BOOL "Build DiskANN Python bindings")
add_subdirectory(${DISKANN_DIR} diskann_build)

# 编译 Puck (如果有 CMakeLists.txt)
if(EXISTS ${PUCK_DIR}/CMakeLists.txt)
    message(STATUS "Building Puck...")
    add_subdirectory(${PUCK_DIR} puck_build)
endif()

# 编译 SPTAG (如果有 CMakeLists.txt)
if(EXISTS ${SPTAG_DIR}/CMakeLists.txt)
    message(STATUS "Building SPTAG...")
    add_subdirectory(${SPTAG_DIR} sptag_build)
endif()

# 添加 pybind11
add_subdirectory(${PYBIND11_DIR} pybind11_build)

# 收集 DiskANN Python 绑定源文件
file(GLOB DISKANN_PYTHON_SOURCES
    "${DISKANN_DIR}/python/src/*.cpp"
)

# 编译 PyCANDYAlgo 模块
message(STATUS "Building PyCANDYAlgo...")
pybind11_add_module(PyCANDYAlgo
    bindings/PyCANDY.cpp
    ${CANDY_SOURCES}
    ${DISKANN_PYTHON_SOURCES}
)

# 查找 torch_python 库
find_library(TORCH_PYTHON_LIBRARY torch_python PATHS "${TORCH_INSTALL_PREFIX}/lib")

# 链接库
target_link_libraries(PyCANDYAlgo PRIVATE
    ${TORCH_LIBRARIES}
    ${TORCH_PYTHON_LIBRARY}
    faiss
    gflags
    glog
    aio
    diskann_s
    SPTAGLibStatic
    puck
    mkl_intel_ilp64
    mkl_intel_thread
    mkl_core
    iomp5
    pthread
    m
    dl
)

# 设置输出目录
set_target_properties(PyCANDYAlgo PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${ALGORITHMS_IMPL_DIR}
    CXX_STANDARD 20
)

# 安装规则
install(TARGETS PyCANDYAlgo
    LIBRARY DESTINATION .
)

message(STATUS "PyCANDYAlgo will be installed to: ${CMAKE_INSTALL_PREFIX}")

install(TARGETS PyCANDYAlgo
    LIBRARY DESTINATION ${Python3_SITELIB}/benchmark_anns/algorithms_impl
)
