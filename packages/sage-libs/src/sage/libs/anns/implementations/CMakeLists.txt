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
set(FAISS_ENABLE_GPU OFF CACHE BOOL "Disable GPU support")
set(FAISS_ENABLE_PYTHON OFF CACHE BOOL "Disable Python binding")
set(BUILD_TESTING OFF CACHE BOOL "Disable tests")
add_subdirectory(${FAISS_DIR} faiss_build)

# Faiss target 将直接在链接时使用
message(STATUS "Faiss library target: faiss")

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

# 收集 DiskANN Python 绑定源文件（排除 module.cpp，因为它定义了独立的 PYBIND11_MODULE）
file(GLOB DISKANN_PYTHON_SOURCES
    "${DISKANN_DIR}/python/src/builder.cpp"
    "${DISKANN_DIR}/python/src/dynamic_memory_index.cpp"
    "${DISKANN_DIR}/python/src/static_disk_index.cpp"
    "${DISKANN_DIR}/python/src/static_memory_index.cpp"
)

# 编译 PyCANDYAlgo 模块
message(STATUS "Building PyCANDYAlgo...")
pybind11_add_module(PyCANDYAlgo
    MODULE
    bindings/PyCANDY.cpp
    ${CANDY_SOURCES}
    ${DISKANN_PYTHON_SOURCES}
)

# 设置模块属性，确保是 Python 扩展模块
set_target_properties(PyCANDYAlgo PROPERTIES
    PREFIX ""
    OUTPUT_NAME "PyCANDYAlgo"
)

# 查找 torch_python 库
find_library(TORCH_PYTHON_LIBRARY torch_python PATHS "${TORCH_INSTALL_PREFIX}/lib" NO_DEFAULT_PATH)
if(NOT TORCH_PYTHON_LIBRARY)
    message(WARNING "torch_python library not found at ${TORCH_INSTALL_PREFIX}/lib, trying Python site-packages")
    execute_process(
        COMMAND ${Python3_EXECUTABLE} -c "import torch; import os; print(os.path.join(os.path.dirname(torch.__file__), 'lib'))"
        OUTPUT_VARIABLE TORCH_LIB_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    find_library(TORCH_PYTHON_LIBRARY torch_python PATHS "${TORCH_LIB_DIR}" NO_DEFAULT_PATH)
endif()

if(TORCH_PYTHON_LIBRARY)
    message(STATUS "Found torch_python: ${TORCH_PYTHON_LIBRARY}")
else()
    message(WARNING "torch_python library not found, linking may fail")
endif()

# 基础链接库 - 注意顺序很重要！
# 使用 WHOLE_ARCHIVE 确保 faiss 的所有符号都被包含
set(PYCANDY_LIBS)

# 第一组：faiss（使用 whole-archive 确保所有符号被导出，并禁用 as-needed）
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    list(APPEND PYCANDY_LIBS -Wl,--no-as-needed -Wl,--whole-archive faiss -Wl,--no-whole-archive -Wl,--as-needed)
else()
    list(APPEND PYCANDY_LIBS faiss)
endif()

# 第二组：Torch
list(APPEND PYCANDY_LIBS ${TORCH_LIBRARIES})

# 第三组：基础系统库
list(APPEND PYCANDY_LIBS gflags pthread dl m)

# 可选: torch_python
if(TORCH_PYTHON_LIBRARY)
    list(APPEND PYCANDY_LIBS ${TORCH_PYTHON_LIBRARY})
endif()

# 必需: glog (必须在 DiskANN 之前，因为 DiskANN 依赖它)
# 尝试多种方式查找 glog
find_package(glog QUIET)
if(glog_FOUND)
    list(APPEND PYCANDY_LIBS glog::glog)
    message(STATUS "Found glog via find_package")
else()
    # 尝试使用 pkg-config
    find_package(PkgConfig QUIET)
    if(PKG_CONFIG_FOUND)
        pkg_check_modules(GLOG libglog QUIET)
        if(GLOG_FOUND)
            list(APPEND PYCANDY_LIBS ${GLOG_LINK_LIBRARIES})
            include_directories(${GLOG_INCLUDE_DIRS})
            message(STATUS "Found glog via pkg-config: ${GLOG_LINK_LIBRARIES}")
        endif()
    endif()

    # 如果还是找不到，尝试直接查找库文件
    if(NOT GLOG_FOUND)
        find_library(GLOG_LIB glog PATHS /usr/lib /usr/local/lib /usr/lib/x86_64-linux-gnu)
        if(GLOG_LIB)
            list(APPEND PYCANDY_LIBS ${GLOG_LIB})
            message(STATUS "Found glog library: ${GLOG_LIB}")
        else()
            # 最后的尝试：直接链接 -lglog
            list(APPEND PYCANDY_LIBS glog)
            message(WARNING "glog not found via find_package or pkg-config, linking with -lglog")
        endif()
    endif()
endif()

# 必需: libaio (DiskANN 需要)
find_library(AIO_LIB aio REQUIRED)
if(NOT AIO_LIB)
    message(FATAL_ERROR "libaio not found - install libaio-dev or libaio-devel")
endif()
list(APPEND PYCANDY_LIBS ${AIO_LIB})
message(STATUS "Found libaio: ${AIO_LIB}")

# 必需: DiskANN (依赖 glog)
if(TARGET diskann_s)
    list(APPEND PYCANDY_LIBS diskann_s)
else()
    message(FATAL_ERROR "diskann_s target not found - DiskANN build failed")
endif()

# 必需: SPTAG
if(TARGET SPTAGLibStatic)
    list(APPEND PYCANDY_LIBS SPTAGLibStatic)
else()
    message(FATAL_ERROR "SPTAGLibStatic target not found - SPTAG build failed")
endif()

# 必需: Puck
if(TARGET puck)
    list(APPEND PYCANDY_LIBS puck)
else()
    message(FATAL_ERROR "puck target not found - Puck build failed")
endif()

# MKL 库（Puck 依赖）- 使用 find_package 或直接查找
if(DEFINED ENV{MKLROOT})
    set(MKLROOT $ENV{MKLROOT})
    message(STATUS "Using MKL from MKLROOT: ${MKLROOT}")

    # 添加 MKL 链接目录
    link_directories(${MKLROOT}/lib/intel64)

    # 按正确顺序链接 MKL
    list(APPEND PYCANDY_LIBS
        mkl_intel_ilp64
        mkl_intel_thread
        mkl_core
        iomp5
    )
else()
    # 尝试直接查找 MKL 库
    find_library(MKL_INTEL_ILP64 mkl_intel_ilp64
        PATHS /opt/intel/oneapi/mkl/latest/lib/intel64 /opt/intel/mkl/lib/intel64
        NO_DEFAULT_PATH)
    find_library(MKL_INTEL_THREAD mkl_intel_thread
        PATHS /opt/intel/oneapi/mkl/latest/lib/intel64 /opt/intel/mkl/lib/intel64
        NO_DEFAULT_PATH)
    find_library(MKL_CORE mkl_core
        PATHS /opt/intel/oneapi/mkl/latest/lib/intel64 /opt/intel/mkl/lib/intel64
        NO_DEFAULT_PATH)
    find_library(IOMP5 iomp5
        PATHS /opt/intel/oneapi/mkl/latest/lib/intel64 /opt/intel/mkl/lib/intel64
              /opt/intel/oneapi/compiler/latest/linux/compiler/lib/intel64_lin
        NO_DEFAULT_PATH)

    if(MKL_INTEL_ILP64 AND MKL_INTEL_THREAD AND MKL_CORE)
        message(STATUS "Found MKL libraries:")
        message(STATUS "  MKL_INTEL_ILP64: ${MKL_INTEL_ILP64}")
        message(STATUS "  MKL_INTEL_THREAD: ${MKL_INTEL_THREAD}")
        message(STATUS "  MKL_CORE: ${MKL_CORE}")
        message(STATUS "  IOMP5: ${IOMP5}")

        list(APPEND PYCANDY_LIBS
            ${MKL_INTEL_ILP64}
            ${MKL_INTEL_THREAD}
            ${MKL_CORE}
        )

        if(IOMP5)
            list(APPEND PYCANDY_LIBS ${IOMP5})
        endif()
    else()
        message(WARNING "MKL libraries not found - Puck may not work properly")
        message(WARNING "Install Intel MKL or set MKLROOT environment variable")
    endif()
endif()

# 系统库已在前面添加

# 重要：使用 LINK_WHAT_YOU_USE 避免未使用符号
set_target_properties(PyCANDYAlgo PROPERTIES
    LINK_WHAT_YOU_USE FALSE
)

# 链接所有库
target_link_libraries(PyCANDYAlgo PRIVATE ${PYCANDY_LIBS})
message(STATUS "PyCANDYAlgo linking order:")
foreach(lib ${PYCANDY_LIBS})
    message(STATUS "  -> ${lib}")
endforeach()

# 设置链接器选项
# 注意：Python 扩展模块需要允许一些由 Python 运行时提供的未定义符号
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    set_target_properties(PyCANDYAlgo PROPERTIES
        LINK_FLAGS "-Wl,--no-as-needed"
    )
endif()

# 设置 RPATH，让 .so 文件在运行时能找到依赖库
# 这样用户不需要每次都设置 LD_LIBRARY_PATH
set(MKL_LIB_DIR "")
if(DEFINED ENV{MKLROOT})
    set(MKL_LIB_DIR "$ENV{MKLROOT}/lib/intel64")
elseif(EXISTS "/opt/intel/oneapi/mkl/latest/lib/intel64")
    set(MKL_LIB_DIR "/opt/intel/oneapi/mkl/latest/lib/intel64")
elseif(EXISTS "/opt/intel/mkl/lib/intel64")
    set(MKL_LIB_DIR "/opt/intel/mkl/lib/intel64")
endif()

# 获取 PyTorch 库路径
execute_process(
    COMMAND ${Python3_EXECUTABLE} -c "import torch; import os; print(os.path.join(os.path.dirname(torch.__file__), 'lib'))"
    OUTPUT_VARIABLE TORCH_LIB_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)

# 构建 RPATH 列表
set(PYCANDY_RPATH "")
if(MKL_LIB_DIR AND EXISTS ${MKL_LIB_DIR})
    list(APPEND PYCANDY_RPATH ${MKL_LIB_DIR})
    message(STATUS "Adding MKL to RPATH: ${MKL_LIB_DIR}")
endif()
if(TORCH_LIB_DIR AND EXISTS ${TORCH_LIB_DIR})
    list(APPEND PYCANDY_RPATH ${TORCH_LIB_DIR})
    message(STATUS "Adding PyTorch to RPATH: ${TORCH_LIB_DIR}")
endif()
# 添加 Intel OpenMP 库路径
if(EXISTS "/opt/intel/oneapi/compiler/latest/lib")
    list(APPEND PYCANDY_RPATH "/opt/intel/oneapi/compiler/latest/lib")
endif()

# 设置输出目录和编译选项
set_target_properties(PyCANDYAlgo PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${ALGORITHMS_IMPL_DIR}
    CXX_STANDARD 20
    # 不设置 SUFFIX，让 pybind11 自动处理
    CXX_VISIBILITY_PRESET "default"
    VISIBILITY_INLINES_HIDDEN OFF
    # 设置 RPATH - 关键！让 .so 文件知道去哪里找动态库
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH "${PYCANDY_RPATH}"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)

# 确保 PyInit_PyCANDYAlgo 符号被导出
target_compile_options(PyCANDYAlgo PRIVATE
    -fvisibility=default
)

# 添加链接选项，确保符号正确导出
target_link_options(PyCANDYAlgo PRIVATE
    -Wl,--export-dynamic
)

# 安装规则 - 简化版本，只安装到当前目录
install(TARGETS PyCANDYAlgo
    LIBRARY DESTINATION ${ALGORITHMS_IMPL_DIR}
    COMPONENT python
)

message(STATUS "PyCANDYAlgo will be built in: ${ALGORITHMS_IMPL_DIR}")
