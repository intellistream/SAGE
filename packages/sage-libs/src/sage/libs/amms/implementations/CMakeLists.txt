
cmake_minimum_required(VERSION 3.14)
project(LibAMM CXX)

# 显示详细编译信息，避免看起来像卡住
set(CMAKE_VERBOSE_MAKEFILE ON)
message(STATUS "=== LibAMM Build Configuration ===")
message(STATUS "CMAKE_BUILD_TYPE: ${CMAKE_BUILD_TYPE}")
message(STATUS "CMAKE_CXX_COMPILER: ${CMAKE_CXX_COMPILER}")

include (cmake/FindCuda.cmake)
include (cmake/FindTorch.cmake)
find_package(Torch REQUIRED)
# Custom CMake find instructions and macros
set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake;${CMAKE_MODULE_PATH}")
include(cmake/macros.cmake)
include(cmake/default.cmake)


# C++ Standard
#set(CMAKE_CXX_STANDARD 20)
#set(CMAKE_CXX_STANDARD_REQUIRED ON)
#gcc 10 g++10

# Unity Build: 合并编译单元以减少头文件重复解析，大幅降低内存占用
set(CMAKE_UNITY_BUILD ON)
set(CMAKE_UNITY_BUILD_BATCH_SIZE 2)  # 每次只合并2个文件，避免单个编译单元过大
message(STATUS "Unity Build enabled with batch size: ${CMAKE_UNITY_BUILD_BATCH_SIZE}")


find_package(Torch REQUIRED)
message(STATUS "Found Torch version: ${Torch_VERSION}")
message(STATUS "Torch libraries: ${TORCH_LIBRARIES}")
#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${TORCH_CXX_FLAGS}")
set(LIBRARIES ${LIBRARIES} ${TORCH_LIBRARIES})
# Set Optimization Flags
# 优化内存使用：降低优化级别，减少调试符号，限制编译器内存
set(CMAKE_CXX_FLAGS "-std=c++20 -Wall -Werror=return-type -Werror=unused-variable -Werror=unused-parameter")
# 内存优化标志：
# -g0: 无调试符号
# -O0: 完全不优化（减少内存）
# -fno-var-tracking: 禁用变量跟踪
# -ftemplate-depth=128: 限制模板实例化深度
# --param ggc-min-expand=20: 更激进的垃圾回收
# --param ggc-min-heapsize=32768: 限制堆大小
set(MEMORY_OPTIMIZATION_FLAGS "-g0 -O0 -fno-var-tracking -ftemplate-depth=128 --param ggc-min-expand=20 --param ggc-min-heapsize=32768")
set(CMAKE_CXX_FLAGS_DEBUG "${MEMORY_OPTIMIZATION_FLAGS} -DNO_RACE_CHECK -DLibAMM_DEBUG_MODE=1")
set(CMAKE_CXX_FLAGS_RELEASE "-Wno-ignored-qualifiers -Wno-sign-compare ${MEMORY_OPTIMIZATION_FLAGS}")
message(STATUS "CXX flags: ${CMAKE_CXX_FLAGS}")
message(STATUS "Memory optimization flags: ${MEMORY_OPTIMIZATION_FLAGS}")
#set(CMAKE_CUDA_STANDARD 11)
#set(CMAKE_CUDA_FLAGS "-std=c++11")
option (ENABLE_OPENCL
        "Enable opencl support"
        OFF
        )
#OPTIONAL OPENCL
if (NOT ENABLE_OPENCL)
    message(STATUS "I will NOT include opencl support ")
    set(LibAMM_CL 0)
else ()
    set(LibAMM_CL 1)
    message(STATUS "I will include opencl support, pls make sure you have corresponding libs")
    set(LIBRARIES ${LIBRARIES} OpenCL)
endif ()
configure_file (
        "${PROJECT_SOURCE_DIR}/include/opencl_config.h.in"
        "${PROJECT_BINARY_DIR}/include/opencl_config.h"
)
option (ENABLE_PAPI
        "Enable papi support, pls first compile papi or set REBUILD_PAPI to ON"
        OFF
        )
# OPTIONAL PAPI
if (NOT ENABLE_PAPI)
    message(STATUS "I will NOT use PAPI ")
    set(LibAMM_PAPI 0)
else ()
    set(LibAMM_PAPI 1)
    message(STATUS "I will try to use PAPI for HW counters, pls make sure your arch supports it")
    option (REBUILD_PAPI
            "Rebuild the papi libs"
            OFF
            )
    if (REBUILD_PAPI)
        set (PAPISCRIPTPATH ../thirdparty)
        execute_process(COMMAND bash ${PAPISCRIPTPATH}/makeClean.sh WORKING_DIRECTORY ${PAPISCRIPTPATH})
        execute_process(COMMAND bash ${PAPISCRIPTPATH}/installPAPI.sh WORKING_DIRECTORY ${PAPISCRIPTPATH})
        message(STATUS "I have rebuilt PAPI" )
    endif()
    find_library (libPAPI libpapi.so ./thirdparty/papi_build/lib)
    message(STATUS "papi Libs= " ${libPAPI} )
    set(LIBRARIES ${LIBRARIES} ${libPAPI})

endif ()
configure_file (
        "${PROJECT_SOURCE_DIR}/include/papi_config.h.in"
        "${PROJECT_BINARY_DIR}/include/papi_config.h"
)

option(ENABLE_PYBIND
        "Enable original pybind and build LibAMM python"
        OFF
)

#set(CMAKE_CUDA_ARCHITECTURES 55)
# Set LOGGING_LEVEL Flag
if (LibAMM_LOGGING_LEVEL)
    get_log_level_value(LibAMM_LOGGING_VALUE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DLibAMM_LOGGING_LEVEL=${LibAMM_LOGGING_VALUE}")
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -DLibAMM_LOGGING_LEVEL=${LibAMM_LOGGING_VALUE}")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -DLibAMM_LOGGING_LEVEL=${LibAMM_LOGGING_VALUE}")
else (LibAMM_LOGGING_LEVEL)
    message("---Everything will be logged")
endif (LibAMM_LOGGING_LEVEL)

message(STATUS "CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS}")
message(STATUS "CMAKE_CXX_FLAGS_DEBUG ${CMAKE_CXX_FLAGS_DEBUG}")
message(STATUS "CMAKE_CXX_FLAGS_RELEASE ${CMAKE_CXX_FLAGS_RELEASE}")
#pytorch
#set(Torch_DIR "/home/tony/.local/lib/python3.10/site-packages/torch/share/cmake" )
# Log4cc
#find_package(Log4cxx REQUIRED)
#include_directories(${Log4cxx_INCLUDE_DIR})
#set(LIBRARIES ${LIBRARIES} ${Log4cxx_LIBRARY})


# 禁用单元测试以减少编译内存占用
option(ENABLE_UNIT_TESTS "Enable unit tests" OFF)
message(STATUS "Enable testing: ${ENABLE_UNIT_TESTS}")


# Print all used include directories
message(STATUS "INCLUDE_DIRS:")
get_property(dirs DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} PROPERTY INCLUDE_DIRECTORIES)
foreach (dir ${dirs})
    message(STATUS "  - ${dir}")
endforeach ()

message(STATUS " Libraries: ${LIBRARIES}")
#add_subdirectory(pytorchNN)
# Add Source Code
add_subdirectory(src)

# Add Library
get_sources(LibAMM_SOURCE_FILES)
get_headers(LibAMM_HEADER_FILES)
add_library(LibAMM SHARED ${LibAMM_SOURCE_FILES} ${LibAMM_HEADER_FILES} ${CMAKE_CURRENT_BINARY_DIR})
set_property(TARGET LibAMM PROPERTY CXX_STANDARD 20)

# 禁用某些有头文件冲突的源文件的 Unity Build
set_source_files_properties(
    "${PROJECT_SOURCE_DIR}/src/myVecAdd.cpp"
    "${PROJECT_SOURCE_DIR}/src/pythonBoundings.cpp"
    PROPERTIES SKIP_UNITY_BUILD_INCLUSION TRUE
)
message(STATUS "Excluded myVecAdd.cpp and pythonBoundings.cpp from Unity Build")

# 禁用预编译头：在低内存环境下PCH反而增加内存占用
# target_precompile_headers(LibAMM PRIVATE include/pch.h)

target_include_directories(LibAMM PUBLIC "include")
target_include_directories(LibAMM PUBLIC "${CMAKE_CURRENT_BINARY_DIR}")
target_include_directories  (LibAMM PUBLIC "thirdparty/papi_build/include")
target_link_libraries(LibAMM PUBLIC ${LIBRARIES})
# 禁用 benchmark 以减少编译内存占用
# add_subdirectory(benchmark)
# set_property(TARGET benchmark PROPERTY CXX_STANDARD 20)
#Add tests (based on GTest suits)
#include(GoogleTest)

if (ENABLE_UNIT_TESTS)
    add_subdirectory(test)
endif ()

if (NOT ENABLE_PYBIND)
    message(STATUS "I will NOT build original python package PyAMM")
    set(LibAMM_PYBIND 0)
else ()
    message(STATUS "I will  build original python package PyAMM")
    find_package(pybind11 CONFIG QUIET)
    if(NOT pybind11_FOUND)
        message(WARNING "pybind11 not found via CMAKE_PREFIX_PATH; fetching minimal copy for build")
        include(FetchContent)
        FetchContent_Declare(
            pybind11
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v2.13.5
            GIT_SHALLOW TRUE
        )
        FetchContent_MakeAvailable(pybind11)
        if(NOT DEFINED pybind11_VERSION)
            set(pybind11_VERSION "2.13.5")
        endif()
    else()
        message(STATUS "Found system pybind11 ${pybind11_VERSION}")
    endif()
    message(STATUS "Using pybind11 ${pybind11_VERSION}")

    pybind11_add_module(PyAMM ${PROJECT_SOURCE_DIR}/src/PyAMM.cpp)
    find_library(TORCH_PYTHON_LIBRARY torch_python PATH "${TORCH_INSTALL_PREFIX}/lib")
    target_link_libraries(PyAMM PUBLIC ${LIBRARIES} LibAMM ${TORCH_PYTHON_LIBRARY})
    install(TARGETS PyAMM LIBRARY DESTINATION .)
    message(STATUS "Additional include torch_python: ${TORCH_PYTHON_LIBRARY}")
    set(LibAMM_PYBIND 1)
    set_property(TARGET PyAMM PROPERTY CXX_STANDARD 20)
    # 禁用 PyAMM 的 Unity Build，因为它太大容易 OOM
    set_target_properties(PyAMM PROPERTIES UNITY_BUILD OFF)
    message(STATUS "Disabled Unity Build for PyAMM to reduce memory usage")
endif ()
configure_file(
        "${PROJECT_SOURCE_DIR}/include/pybind_config.h.in"
        "${PROJECT_BINARY_DIR}/include/pybind_config.h"
)

install(DIRECTORY "include" DESTINATION "/LibAMM" COMPONENT LibAMM)
# copy scripts
file(GLOB allCopyFiles "${PROJECT_SOURCE_DIR}/scripts/*")
file(COPY ${allCopyFiles} DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/benchmark/scripts)
file(COPY ${allCopyFiles} DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/benchmark/scripts)

# copy files needed for real world matrix loader
# Allow external projects to specify dataset path or disable dataset copy
option(LIBAMM_SKIP_DATASET_COPY "Skip copying benchmark datasets" OFF)
set(LIBAMM_DATASET_SOURCE_DIR "${CMAKE_SOURCE_DIR}/benchmark/datasets" CACHE PATH "Path to LibAMM benchmark datasets")

if(NOT LIBAMM_SKIP_DATASET_COPY)
    if(EXISTS "${LIBAMM_DATASET_SOURCE_DIR}")
        message(STATUS "Copying LibAMM datasets from: ${LIBAMM_DATASET_SOURCE_DIR}")
        set(source_directory "${LIBAMM_DATASET_SOURCE_DIR}/")
        set(destination_directory "${CMAKE_BINARY_DIR}/benchmark/datasets/")
        file(COPY ${source_directory} DESTINATION ${destination_directory})
    else()
        message(STATUS "LibAMM datasets not found at ${LIBAMM_DATASET_SOURCE_DIR}, skipping dataset copy")
        message(STATUS "Set LIBAMM_DATASET_SOURCE_DIR to specify a different path, or set LIBAMM_SKIP_DATASET_COPY=ON to disable")
    endif()
else()
    message(STATUS "LibAMM dataset copy disabled (LIBAMM_SKIP_DATASET_COPY=ON)")
endif()
