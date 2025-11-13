cmake_minimum_required(VERSION 3.10...3.27)
project(
    ${SKBUILD_PROJECT_NAME}
    VERSION ${SKBUILD_PROJECT_VERSION}
    LANGUAGES CXX C
)

# ============================================================================
# 全局编译设置
# ============================================================================
set(CMAKE_CXX_STANDARD 17)
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

message(STATUS "")
message(STATUS "=== SAGE Libs Build Configuration ===")
message(STATUS "Python: ${Python_VERSION}")
message(STATUS "pybind11: ${pybind11_VERSION}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "======================================")
message(STATUS "")

# ============================================================================
# LibAMM - Approximate Matrix Multiplication Library
# ============================================================================
set(LIBAMM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/libs/libamm")

# 设置统一的构建输出目录
set(SAGE_BUILD_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../.sage/build")

if(EXISTS "${LIBAMM_DIR}/CMakeLists.txt")
    message(STATUS "Adding LibAMM submodule...")
    message(STATUS "  Build output: ${SAGE_BUILD_ROOT}/libamm")

    # 检查 PyTorch 是否可用（LibAMM 需要）
    execute_process(
        COMMAND ${Python_EXECUTABLE} -c "import torch; print(torch.__version__)"
        RESULT_VARIABLE TORCH_CHECK_RESULT
        OUTPUT_VARIABLE TORCH_VERSION
        ERROR_QUIET
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )

    if(TORCH_CHECK_RESULT EQUAL 0)
        message(STATUS "  PyTorch found: ${TORCH_VERSION}")

        # 检查 PyTorch 是否为 CUDA 版本（通过版本字符串检测，如 "2.7.1+cu126"）
        string(FIND "${TORCH_VERSION}" "+cu" CUDA_POS)
        if(NOT CUDA_POS EQUAL -1)
            # PyTorch 是 CUDA 版本
            message(STATUS "  PyTorch type: CUDA version detected")
            find_program(NVCC_EXECUTABLE nvcc)
            if(NOT NVCC_EXECUTABLE)
                message(STATUS "  CUDA compiler (nvcc) not found")
                message(STATUS "  ")
                message(STATUS "========================================")
                message(STATUS "  自动切换到 CPU 版本的 PyTorch")
                message(STATUS "========================================")
                message(STATUS "")
                message(STATUS "LibAMM 需要编译 C++ 扩展，但检测到：")
                message(STATUS "  - PyTorch 版本: ${TORCH_VERSION} (CUDA)")
                message(STATUS "  - CUDA 编译器: 未找到")
                message(STATUS "")
                message(STATUS "将自动安装 CPU 版本的 PyTorch...")
                message(STATUS "")

                # 自动安装 CPU 版本的 PyTorch
                execute_process(
                    COMMAND ${Python_EXECUTABLE} -m pip install --force-reinstall
                            "torch>=2.0.0" --index-url https://download.pytorch.org/whl/cpu
                    RESULT_VARIABLE TORCH_INSTALL_RESULT
                    OUTPUT_VARIABLE TORCH_INSTALL_OUTPUT
                    ERROR_VARIABLE TORCH_INSTALL_ERROR
                )

                if(TORCH_INSTALL_RESULT EQUAL 0)
                    message(STATUS "✅ 成功安装 CPU 版本的 PyTorch")
                    message(STATUS "   现在可以继续编译 LibAMM...")
                    message(STATUS "========================================")
                    message(STATUS "")
                else()
                    message(FATAL_ERROR "❌ 无法自动安装 CPU 版本的 PyTorch\n${TORCH_INSTALL_ERROR}")
                endif()
            else()
                message(STATUS "  CUDA compiler found: ${NVCC_EXECUTABLE}")
                message(STATUS "  Will build LibAMM with CUDA support")
            endif()
        else()
            # PyTorch 是 CPU 版本
            message(STATUS "  PyTorch type: CPU-only")
            message(STATUS "  Perfect for LibAMM CPU-only build")
        endif()

        message(STATUS "  Building LibAMM...")

        # 设置 LibAMM 的编译选项
        set(BUILD_BENCHMARK OFF CACHE BOOL "Skip LibAMM benchmark" FORCE)
        set(ENABLE_PYBIND ON CACHE BOOL "Enable Python bindings" FORCE)
        set(ENABLE_HDF5 ON CACHE BOOL "Enable HDF5 support" FORCE)
        set(ENABLE_PAPI OFF CACHE BOOL "Disable PAPI" FORCE)

        # 设置 CUDACXX 环境变量（即使不存在 nvcc 也设置，参考 buildCPUOnly.sh）
        set(ENV{CUDACXX} "/usr/local/cuda/bin/nvcc")

        add_subdirectory(${LIBAMM_DIR} ${SAGE_BUILD_ROOT}/libamm)
        message(STATUS "  ✓ LibAMM configured (with NumPy interface)")
    else()
        message(WARNING "  PyTorch not found - skipping LibAMM build")
        message(WARNING "  To build LibAMM, install with: pip install isage-libs[amm]")
        message(WARNING "  Or install PyTorch: pip install torch>=2.0.0")
    endif()
else()
    message(WARNING "LibAMM submodule not found at ${LIBAMM_DIR}")
    message(WARNING "  To build LibAMM, ensure the submodule is initialized")
endif()

# ============================================================================
# 配置摘要
# ============================================================================
message(STATUS "")
message(STATUS "SAGE Libs C++ Extensions - Build Summary")
message(STATUS "=========================================")
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
if(TARGET PyAMM)
    message(STATUS "  ✓ LibAMM (PyAMM)")
else()
    message(STATUS "  ✗ LibAMM (not configured)")
endif()
message(STATUS "=========================================")
message(STATUS "")

# ============================================================================
# 安装 Python 源文件
# ============================================================================
# scikit-build-core 需要明确告知要安装哪些 Python 文件
# 这确保纯 Python 代码（如 sage.libs.context.compression）也被正确安装
message(STATUS "Configuring Python source installation...")

# 安装所有 Python 包到 site-packages/sage
install(
    DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src/sage/"
    DESTINATION "${SKBUILD_PLATLIB_DIR}/sage"
    COMPONENT python
    FILES_MATCHING
    PATTERN "*.py"
    PATTERN "*.pyi"
    PATTERN "py.typed"
    PATTERN "__pycache__" EXCLUDE
    PATTERN "*.pyc" EXCLUDE
    PATTERN ".pytest_cache" EXCLUDE
    PATTERN "tests" EXCLUDE
)

message(STATUS "  ✓ Python source files will be installed to: ${SKBUILD_PLATLIB_DIR}/sage")
message(STATUS "")
