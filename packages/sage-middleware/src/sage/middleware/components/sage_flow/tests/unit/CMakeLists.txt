# 单元测试 CMakeLists.txt

# 启用测试
enable_testing()

# 收集所有单元测试源文件
set(UNIT_TEST_SOURCES
    test_message_system.cpp
    test_stream_engine.cpp
    test_operators.cpp
    test_functions.cpp
    test_indices.cpp
    test_datastream.cpp
)

# Gcov覆盖率支持
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fprofile-arcs -ftest-coverage")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fprofile-arcs -ftest-coverage")
endif()

# 为每个测试文件创建独立的可执行文件
foreach(test_source ${UNIT_TEST_SOURCES})
    # 获取不带扩展名的文件名
    get_filename_component(test_name ${test_source} NAME_WE)

    # 创建测试可执行文件
    add_executable(${test_name} ${test_source})

    # 链接库
    target_link_libraries(${test_name}
        PRIVATE
            sage_flow_engine
            sage_flow_datastream_lib
            GTest::gtest
            GTest::gtest_main
            Threads::Threads
    )

    # 设置包含目录
    target_include_directories(${test_name}
        PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/../../include
            ${CMAKE_CURRENT_SOURCE_DIR}/../../src
    )

    # 添加到 CTest
    add_test(
        NAME ${test_name}
        COMMAND ${test_name}
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    )

    # 设置测试属性
    set_tests_properties(${test_name}
        PROPERTIES
            TIMEOUT 300  # 5分钟超时
            LABELS "unit"
    )
endforeach()

# 创建统一的单元测试目标
add_custom_target(unit_tests
    DEPENDS ${UNIT_TEST_SOURCES}
    COMMENT "构建所有单元测试"
)

# 运行所有单元测试的目标
add_custom_target(run_unit_tests
    COMMAND ${CMAKE_CTEST_COMMAND} -L unit --output-on-failure
    DEPENDS unit_tests
    COMMENT "运行所有单元测试"
)

# 覆盖率报告目标
add_custom_target(coverage
    COMMAND lcov --directory . --capture --output-file coverage.info
    COMMAND genhtml coverage.info --output-directory coverage_report
    COMMAND echo "覆盖率报告生成在 coverage_report/index.html"
    DEPENDS unit_tests
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "生成覆盖率报告"
)

# 集成测试目标
add_custom_target(integration_tests
    COMMAND ${CMAKE_CTEST_COMMAND} -L integration --output-on-failure
    COMMENT "运行集成测试"
)

# 完整测试套件
add_custom_target(all_tests
    COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
    DEPENDS unit_tests integration_tests
    COMMENT "运行所有测试"
)