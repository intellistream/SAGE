# 性能基准测试 CMakeLists.txt

# 检查存在的性能测试源文件
set(POTENTIAL_PERFORMANCE_SOURCES
    test_throughput_benchmark.cpp
    test_latency_benchmark.cpp
    test_memory_benchmark.cpp
    test_concurrency_benchmark.cpp
)

set(PERFORMANCE_TEST_SOURCES "")
foreach(test_source ${POTENTIAL_PERFORMANCE_SOURCES})
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${test_source})
        list(APPEND PERFORMANCE_TEST_SOURCES ${test_source})
    endif()
endforeach()

# 检查存在的Python性能测试文件
set(POTENTIAL_PYTHON_PERFORMANCE_TESTS
    test_performance_benchmarks.py
)

set(PYTHON_PERFORMANCE_TESTS "")
foreach(test_file ${POTENTIAL_PYTHON_PERFORMANCE_TESTS})
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${test_file})
        list(APPEND PYTHON_PERFORMANCE_TESTS ${test_file})
    endif()
endforeach()

# 为每个存在的 C++ 性能测试创建可执行文件
if(PERFORMANCE_TEST_SOURCES)
    message(STATUS "找到C++性能测试文件: ${PERFORMANCE_TEST_SOURCES}")
    foreach(test_source ${PERFORMANCE_TEST_SOURCES})
        get_filename_component(test_name ${test_source} NAME_WE)
        
        add_executable(${test_name} ${test_source})
        
        target_link_libraries(${test_name}
            PRIVATE
                ${TEST_LIBRARIES}
                pthread
        )
        
        target_include_directories(${test_name}
            PRIVATE
                ${CMAKE_CURRENT_SOURCE_DIR}/../../include
                ${CMAKE_CURRENT_SOURCE_DIR}/../common
        )
        
        # 性能测试通常需要更长时间
        add_test(
            NAME performance_${test_name}
            COMMAND ${test_name}
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        )
        
        set_tests_properties(performance_${test_name}
            PROPERTIES
                TIMEOUT 1200  # 20分钟超时
                LABELS "performance;benchmark"
        )
        
        # 性能测试特定的编译选项
        target_compile_definitions(${test_name}
            PRIVATE
                PERFORMANCE_TESTING=1
                BENCHMARK_MODE=1
        )
        
        # 优化版本用于性能测试
        if(CMAKE_BUILD_TYPE STREQUAL "Release")
            target_compile_options(${test_name} PRIVATE -O3 -DNDEBUG)
        endif()
    endforeach()
else()
    message(STATUS "未找到C++性能测试文件，跳过C++性能测试")
endif()

# Python 性能测试
if(PYTHON_PERFORMANCE_TESTS)
    message(STATUS "找到Python性能测试文件: ${PYTHON_PERFORMANCE_TESTS}")
    foreach(test_file ${PYTHON_PERFORMANCE_TESTS})
        get_filename_component(test_name ${test_file} NAME_WE)
        
        add_test(
            NAME performance_py_${test_name}
            COMMAND ${Python3_EXECUTABLE} -m pytest ${CMAKE_CURRENT_SOURCE_DIR}/${test_file} -v --benchmark-only
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        )
        
        set_tests_properties(performance_py_${test_name}
            PROPERTIES
                TIMEOUT 1800  # 30分钟超时
                LABELS "performance;python;benchmark"
                ENVIRONMENT "PYTHONPATH=${CMAKE_BINARY_DIR}:$ENV{PYTHONPATH}"
        )
    endforeach()
else()
    message(STATUS "未找到Python性能测试文件，跳过Python性能测试")
endif()

# 创建性能测试目标（仅当有测试文件时）
if(PERFORMANCE_TEST_SOURCES OR PYTHON_PERFORMANCE_TESTS)
    add_custom_target(performance_tests
        COMMENT "构建所有性能测试"
    )
else()
    message(STATUS "未找到性能测试文件，跳过性能测试目标创建")
endif()

# 运行所有性能测试
add_custom_target(run_performance_tests
    COMMAND ${CMAKE_CTEST_COMMAND} -L performance --output-on-failure
    DEPENDS performance_tests sage_flow_core
    COMMENT "运行所有性能基准测试"
)

# 生成性能报告
add_custom_target(performance_report
    COMMAND ${CMAKE_COMMAND} -E echo "生成性能基准报告..."
    COMMAND ${CMAKE_CTEST_COMMAND} -L performance --output-junit performance_results.xml
    DEPENDS run_performance_tests
    COMMENT "生成性能测试报告"
)

# 基准数据目录
set(BENCHMARK_DATA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/data)
if(EXISTS ${BENCHMARK_DATA_DIR})
    file(COPY ${BENCHMARK_DATA_DIR} DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
endif()

# 性能测试配置
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/benchmark_config.json.in
    ${CMAKE_CURRENT_BINARY_DIR}/benchmark_config.json
    @ONLY
)