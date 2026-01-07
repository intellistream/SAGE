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

message(STATUS "")
message(STATUS "=== SAGE Libs Build Configuration ===")
message(STATUS "Python: ${Python_VERSION}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "")
message(STATUS "Note: sage-libs is a pure Python package.")
message(STATUS "C++ extensions (ANNS, AMM) have been moved to independent packages:")
message(STATUS "  - isage-anns (ANNS algorithms)")
message(STATUS "  - isage-amms (AMM algorithms)")
message(STATUS "Install them separately if needed: pip install isage-anns isage-amms")
message(STATUS "======================================")
message(STATUS "")

# ============================================================================
# 配置摘要
# ============================================================================
message(STATUS "")
message(STATUS "SAGE Libs Build Summary")
message(STATUS "=========================================")
message(STATUS "Project: ${SKBUILD_PROJECT_NAME} v${SKBUILD_PROJECT_VERSION}")
message(STATUS "Python: ${Python_VERSION}")
message(STATUS "C++ Standard: C++${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "")
message(STATUS "🔍 SKBUILD Variables:")
message(STATUS "  SKBUILD_STATE: ${SKBUILD_STATE}")
message(STATUS "  SKBUILD_PLATLIB_DIR: ${SKBUILD_PLATLIB_DIR}")
message(STATUS "")
message(STATUS "Extensions: None (pure Python package)")
message(STATUS "=========================================")
message(STATUS "")

# ============================================================================
# 安装 Python 源文件
# ============================================================================
# scikit-build-core 需要明确告知要安装哪些 Python 文件
# 这确保纯 Python 代码（如 sage.libs.context.compression）也被正确安装
#
# 注意：在 editable 模式下跳过文件复制，让 scikit-build-core 的 redirect 模式生效
# SKBUILD_STATE 可能的值: "wheel", "editable", "sdist", "metadata_wheel", "metadata_editable"
# ============================================================================
if(SKBUILD_STATE STREQUAL "editable" OR SKBUILD_STATE STREQUAL "metadata_editable")
    message(STATUS "")
    message(STATUS "========================================")
    message(STATUS "  Editable mode detected - skipping Python file installation")
    message(STATUS "  Source files will be used directly from: ${CMAKE_CURRENT_SOURCE_DIR}/src/sage/")
    message(STATUS "========================================")
    message(STATUS "")
else()
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
endif()
