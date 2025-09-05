# 单元测试 CMakeLists.txt

# 收集所有单元测试源文件
set(UNIT_TEST_SOURCES
    test_message_system.cpp
    test_stream_engine.cpp
    test_operators.cpp
    test_functions.cpp
    test_indices.cpp
    test_datastream.cpp
)

# 为每个测试文件创建独立的可执行文件
foreach(test_source ${UNIT_TEST_SOURCES})
    # 获取不带扩展名的文件名
    get_filename_component(test_name ${test_source} NAME_WE)
    
    # 创建测试可执行文件
    add_executable(${test_name} ${test_source})
    
    # 链接库
    target_link_libraries(${test_name}
        PRIVATE
            ${TEST_LIBRARIES}
            pthread  # 对于并发测试
    )
    
    # 设置包含目录
    target_include_directories(${test_name}
        PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/../../include
            ${CMAKE_CURRENT_SOURCE_DIR}/../common
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