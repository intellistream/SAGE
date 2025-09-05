# 集成测试 CMakeLists.txt

# 收集所有集成测试源文件
set(INTEGRATION_TEST_SOURCES
    test_sage_integration.py
    test_end_to_end.py
    test_performance.py
)

# 对于 Python 集成测试，我们需要确保 Python 环境正确设置
find_package(Python3 COMPONENTS Interpreter REQUIRED)

# 创建集成测试目标
add_custom_target(integration_tests
    COMMENT "准备集成测试"
)

# 为每个 Python 测试文件创建测试
foreach(test_source ${INTEGRATION_TEST_SOURCES})
    # 获取不带扩展名的文件名
    get_filename_component(test_name ${test_source} NAME_WE)
    
    # 添加 Python 测试到 CTest
    add_test(
        NAME integration_${test_name}
        COMMAND ${Python3_EXECUTABLE} -m pytest ${CMAKE_CURRENT_SOURCE_DIR}/${test_source} -v
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    )
    
    # 设置测试属性
    set_tests_properties(integration_${test_name}
        PROPERTIES
            TIMEOUT 600  # 10分钟超时
            LABELS "integration"
            ENVIRONMENT "PYTHONPATH=${CMAKE_BINARY_DIR}:$ENV{PYTHONPATH}"
    )
    
    # 确保在运行测试前构建了核心库
    set_tests_properties(integration_${test_name}
        PROPERTIES
            DEPENDS sage_flow_core
    )
endforeach()

# 创建 C++ 集成测试（仅在文件存在时）
set(POTENTIAL_CPP_INTEGRATION_TESTS
    test_cpp_integration.cpp
)

set(CPP_INTEGRATION_TESTS "")
foreach(test_source ${POTENTIAL_CPP_INTEGRATION_TESTS})
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${test_source})
        list(APPEND CPP_INTEGRATION_TESTS ${test_source})
    endif()
endforeach()

if(CPP_INTEGRATION_TESTS)
    message(STATUS "找到C++集成测试文件: ${CPP_INTEGRATION_TESTS}")
    foreach(test_source ${CPP_INTEGRATION_TESTS})
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
        
        add_test(
            NAME integration_${test_name}
            COMMAND ${test_name}
            WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        )
        
        set_tests_properties(integration_${test_name}
            PROPERTIES
                TIMEOUT 600
                LABELS "integration;cpp"
        )
    endforeach()
else()
    message(STATUS "未找到C++集成测试文件，跳过C++集成测试")
endif()

# 运行所有集成测试的目标
add_custom_target(run_integration_tests
    COMMAND ${CMAKE_CTEST_COMMAND} -L integration --output-on-failure
    DEPENDS integration_tests sage_flow_core
    COMMENT "运行所有集成测试"
)

# 集成测试数据目录
set(INTEGRATION_TEST_DATA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/data)
if(EXISTS ${INTEGRATION_TEST_DATA_DIR})
    # 复制测试数据到构建目录
    file(COPY ${INTEGRATION_TEST_DATA_DIR} DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
endif()

# 环境检查测试
add_test(
    NAME integration_environment_check
    COMMAND ${Python3_EXECUTABLE} -c "
import sys
print(f'Python version: {sys.version}')
try:
    import sage_flow_datastream
    print('SAGE Flow module imported successfully')
except ImportError as e:
    print(f'Failed to import SAGE Flow module: {e}')
    sys.exit(1)
"
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)

set_tests_properties(integration_environment_check
    PROPERTIES
        LABELS "integration;environment"
        TIMEOUT 30
)