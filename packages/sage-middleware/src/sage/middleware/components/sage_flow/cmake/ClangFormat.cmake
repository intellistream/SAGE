# ClangFormat Configuration
# 集成 clang-format 到 CMake 构建系统中

find_program(CLANG_FORMAT_EXE clang-format)

if(CLANG_FORMAT_EXE)
    # 获取 clang-format 版本
    execute_process(
        COMMAND ${CLANG_FORMAT_EXE} --version
        OUTPUT_VARIABLE CLANG_FORMAT_VERSION
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    message(STATUS "Found clang-format: ${CLANG_FORMAT_EXE} (${CLANG_FORMAT_VERSION})")

    # 查找所有需要格式化的文件
    file(GLOB_RECURSE ALL_CPP_FILES
        ${CMAKE_SOURCE_DIR}/src/*.cpp
        ${CMAKE_SOURCE_DIR}/src/*.hpp
        ${CMAKE_SOURCE_DIR}/src/*.h
        ${CMAKE_SOURCE_DIR}/include/*.cpp
        ${CMAKE_SOURCE_DIR}/include/*.hpp
        ${CMAKE_SOURCE_DIR}/include/*.h
    )

    # 过滤掉构建目录中的文件
    set(CPP_FILES)
    foreach(file ${ALL_CPP_FILES})
        if(NOT file MATCHES "${CMAKE_BINARY_DIR}")
            list(APPEND CPP_FILES ${file})
        endif()
    endforeach()

    # 创建格式化目标
    add_custom_target(format
        COMMAND ${CLANG_FORMAT_EXE} -i ${CPP_FILES}
        COMMENT "Running clang-format on all source files"
        VERBATIM
    )

    # 创建检查格式目标（不修改文件，只检查）
    add_custom_target(format-check
        COMMAND ${CLANG_FORMAT_EXE} --dry-run -Werror --ferror-limit=1 ${CPP_FILES}
        COMMENT "Checking code formatting with clang-format"
        VERBATIM
    )

    # 创建格式化检查目标（用于CI/CD）
    add_custom_target(format-check-ci
        COMMAND ${CLANG_FORMAT_EXE} --dry-run -Werror ${CPP_FILES} > /dev/null 2>&1 || (echo "Code formatting issues found. Run 'make format' to fix." && exit 1)
        COMMENT "Checking code formatting for CI/CD"
    )

    # 将格式化目标设置为可选依赖
    if(SAGE_FLOW_ENABLE_CLANG_FORMAT)
        message(STATUS "ClangFormat integration enabled")
        message(STATUS "Available targets:")
        message(STATUS "  format        - Format all source files")
        message(STATUS "  format-check  - Check formatting without modifying files")
        message(STATUS "  format-check-ci - Check formatting for CI/CD (fails on issues)")
    endif()

else()
    message(WARNING "clang-format not found. Install with: sudo apt-get install clang-format (Ubuntu/Debian) or brew install clang-format (macOS)")
endif()