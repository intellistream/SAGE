# SAGE Flow 测试 CMakeLists.txt

cmake_minimum_required(VERSION 3.16)

# 查找 GoogleTest
find_package(GTest QUIET)

if(NOT GTest_FOUND)
    # 如果没有找到系统安装的 GoogleTest，使用 FetchContent 下载
    include(FetchContent)
    
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG        release-1.12.1
    )
    
    # 为了 Windows 防止覆盖父项目的编译器/链接器设置
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    
    FetchContent_MakeAvailable(googletest)
    
    # 创建别名以匹配系统安装的目标名称
    add_library(GTest::gtest ALIAS gtest)
    add_library(GTest::gtest_main ALIAS gtest_main)
    add_library(GTest::gmock ALIAS gmock)
    add_library(GTest::gmock_main ALIAS gmock_main)
endif()

# 设置测试包含目录
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../include)

# 包含 Sanitizer 配置模块
if(ENABLE_DEV_TOOLS)
    include(${CMAKE_CURRENT_SOURCE_DIR}/../cmake/SanitizersConfig.cmake)
endif()

# 创建测试库目标
set(TEST_LIBRARIES
    sage_flow_datastream_lib
    sage_flow_engine
    sage_flow_message
    sage_flow_operator
    sage_flow_function
    sage_flow_index
    sage_flow_memory
    GTest::gtest
    GTest::gtest_main
    GTest::gmock
    GTest::gmock_main
)

# 添加编译器标志
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    add_compile_options(-Wno-unused-parameter -Wno-sign-compare)
endif()

# 移除静态链接选项以避免兼容性问题
set(STATIC_LINK_OPTIONS "")

# ============================================================================
# Sanitizer 测试支持函数
# ============================================================================

# 为测试目标应用 sanitizer 配置
function(sage_add_sanitizer_test TEST_NAME TEST_SOURCE)
    # 创建测试可执行文件
    add_executable(${TEST_NAME} ${TEST_SOURCE})

    # 链接测试库
    target_link_libraries(${TEST_NAME} ${TEST_LIBRARIES})

    # 应用静态链接选项以避免GLIBC版本问题
    target_link_options(${TEST_NAME} PRIVATE ${STATIC_LINK_OPTIONS})

    # 应用 sanitizer 配置
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        sage_apply_sanitizers(${TEST_NAME})
    endif()

    # 添加到测试套件
    add_test(NAME ${TEST_NAME} COMMAND ${TEST_NAME})

    # 设置测试属性
    sage_configure_sanitizer_test_properties(${TEST_NAME})
endfunction()

# 配置 sanitizer 测试属性和环境变量
function(sage_configure_sanitizer_test_properties TEST_NAME)
    # 设置测试超时（sanitizer 可能会减慢执行速度）
    set_tests_properties(${TEST_NAME} PROPERTIES TIMEOUT 300)
    
    # 设置 sanitizer 环境变量
    if(SAGE_SANITIZER_ENV_VARS)
        set_tests_properties(${TEST_NAME} PROPERTIES
            ENVIRONMENT "${SAGE_SANITIZER_ENV_VARS}"
        )
    endif()
    
    # 设置测试标签
    set(TEST_LABELS "")
    if(SAGE_SANITIZER_ADDRESS)
        list(APPEND TEST_LABELS "asan")
    endif()
    if(SAGE_SANITIZER_MEMORY)
        list(APPEND TEST_LABELS "msan")
    endif()
    if(SAGE_SANITIZER_THREAD)
        list(APPEND TEST_LABELS "tsan")
    endif()
    if(SAGE_SANITIZER_UNDEFINED)
        list(APPEND TEST_LABELS "ubsan")
    endif()
    if(SAGE_SANITIZER_LEAK)
        list(APPEND TEST_LABELS "lsan")
    endif()
    
    if(TEST_LABELS)
        set_tests_properties(${TEST_NAME} PROPERTIES LABELS "${TEST_LABELS}")
    endif()
    
    # 为有问题的 sanitizer 组合设置预期失败
    if(SAGE_SANITIZER_MEMORY AND SAGE_SANITIZER_THREAD)
        set_tests_properties(${TEST_NAME} PROPERTIES
            WILL_FAIL TRUE
            SKIP_RETURN_CODE 77
        )
    endif()
endfunction()

# 创建 sanitizer 特定的测试目标
function(sage_create_sanitizer_test_targets)
    # AddressSanitizer 测试目标
    add_custom_target(test_asan
        COMMAND ${CMAKE_COMMAND}
            -DSAGE_SANITIZER_ADDRESS=ON
            -DSAGE_SANITIZER_LEVEL=medium
            -DCMAKE_BUILD_TYPE=Debug
            ${CMAKE_SOURCE_DIR}
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}
        COMMAND ${CMAKE_CTEST_COMMAND} -L "asan" --output-on-failure
        COMMENT "运行 AddressSanitizer 测试"
    )
    
    # MemorySanitizer 测试目标 (仅 Clang)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        add_custom_target(test_msan
            COMMAND ${CMAKE_COMMAND}
                -DSAGE_SANITIZER_MEMORY=ON
                -DSAGE_SANITIZER_LEVEL=medium
                -DCMAKE_BUILD_TYPE=Debug
                ${CMAKE_SOURCE_DIR}
            COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}
            COMMAND ${CMAKE_CTEST_COMMAND} -L "msan" --output-on-failure
            COMMENT "运行 MemorySanitizer 测试"
        )
    endif()
    
    # ThreadSanitizer 测试目标
    add_custom_target(test_tsan
        COMMAND ${CMAKE_COMMAND}
            -DSAGE_SANITIZER_THREAD=ON
            -DSAGE_SANITIZER_LEVEL=medium
            -DCMAKE_BUILD_TYPE=Debug
            ${CMAKE_SOURCE_DIR}
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}
        COMMAND ${CMAKE_CTEST_COMMAND} -L "tsan" --output-on-failure
        COMMENT "运行 ThreadSanitizer 测试"
    )
    
    # UndefinedBehaviorSanitizer 测试目标
    add_custom_target(test_ubsan
        COMMAND ${CMAKE_COMMAND}
            -DSAGE_SANITIZER_UNDEFINED=ON
            -DSAGE_SANITIZER_LEVEL=aggressive
            -DCMAKE_BUILD_TYPE=Debug
            ${CMAKE_SOURCE_DIR}
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}
        COMMAND ${CMAKE_CTEST_COMMAND} -L "ubsan" --output-on-failure
        COMMENT "运行 UndefinedBehaviorSanitizer 测试"
    )
    
    # LeakSanitizer 测试目标
    add_custom_target(test_lsan
        COMMAND ${CMAKE_COMMAND}
            -DSAGE_SANITIZER_LEAK=ON
            -DSAGE_SANITIZER_LEVEL=medium
            -DCMAKE_BUILD_TYPE=Debug
            ${CMAKE_SOURCE_DIR}
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}
        COMMAND ${CMAKE_CTEST_COMMAND} -L "lsan" --output-on-failure
        COMMENT "运行 LeakSanitizer 测试"
    )
    
    # 所有 sanitizer 测试目标
    add_custom_target(test_all_sanitizers
        COMMAND ${CMAKE_COMMAND}
            -DSAGE_SANITIZER_ADDRESS=ON
            -DSAGE_SANITIZER_UNDEFINED=ON
            -DSAGE_SANITIZER_LEAK=ON
            -DSAGE_SANITIZER_LEVEL=comprehensive
            -DCMAKE_BUILD_TYPE=Debug
            ${CMAKE_SOURCE_DIR}
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}
        COMMAND ${CMAKE_CTEST_COMMAND} -L "asan|ubsan|lsan" --output-on-failure
        COMMENT "运行所有兼容的 sanitizer 测试"
    )
endfunction()

# 单元测试
add_subdirectory(unit)

# 集成测试
add_subdirectory(integration)

# 性能测试
add_subdirectory(performance)

# CandyFlow 功能测试
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/candyflow)
    add_subdirectory(candyflow)
endif()

# 创建测试目标
add_custom_target(run_all_tests
    COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure --parallel ${CMAKE_BUILD_PARALLEL_LEVEL}
    DEPENDS 
        unit_tests
        integration_tests
        performance_tests
    COMMENT "运行所有测试"
)

# 测试发现
enable_testing()

# 添加测试报告生成
add_custom_target(test_report
    COMMAND ${CMAKE_CTEST_COMMAND} --output-junit test_results.xml --output-on-failure
    DEPENDS run_all_tests
    COMMENT "生成测试报告"
)

# 代码覆盖率（仅在 Debug 模式下）
if(CMAKE_BUILD_TYPE STREQUAL "Debug" AND CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    option(ENABLE_COVERAGE "Enable code coverage" OFF)
    
    if(ENABLE_COVERAGE)
        add_compile_options(--coverage -O0)
        add_link_options(--coverage)
        
        # 查找 gcov 和 lcov
        find_program(GCOV_PATH gcov)
        find_program(LCOV_PATH lcov)
        find_program(GENHTML_PATH genhtml)
        
        if(LCOV_PATH AND GENHTML_PATH)
            add_custom_target(coverage
                COMMAND ${LCOV_PATH} --capture --directory . --output-file coverage.info
                COMMAND ${LCOV_PATH} --remove coverage.info '/usr/*' --output-file coverage.info
                COMMAND ${LCOV_PATH} --remove coverage.info '*/tests/*' --output-file coverage.info
                COMMAND ${GENHTML_PATH} coverage.info --output-directory coverage_report
                DEPENDS run_all_tests
                COMMENT "生成代码覆盖率报告"
            )
        endif()
    endif()
endif()

# 创建 sanitizer 测试目标
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    sage_create_sanitizer_test_targets()
    
    # 打印 sanitizer 测试配置信息
    message(STATUS "Sanitizer 测试目标已创建:")
    message(STATUS "  test_asan - AddressSanitizer 测试")
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        message(STATUS "  test_msan - MemorySanitizer 测试")
    endif()
    message(STATUS "  test_tsan - ThreadSanitizer 测试")
    message(STATUS "  test_ubsan - UndefinedBehaviorSanitizer 测试")
    message(STATUS "  test_lsan - LeakSanitizer 测试")
    message(STATUS "  test_all_sanitizers - 所有兼容的 sanitizer 测试")
endif()