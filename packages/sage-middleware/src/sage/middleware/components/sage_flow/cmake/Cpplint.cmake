# Cpplint Configuration
# 集成 cpplint 到 CMake 构建系统中

find_program(CPPLINT_EXE cpplint)

if(CPPLINT_EXE)
    # 设置 cpplint 属性
    set(CPPLINT_ARGS
        --linelength=80
        --filter=-legal/copyright,-build/include_subdir,-build/include_order
    )

    # 为所有 C++ 源文件和头文件添加 cpplint 检查
    function(add_cpplint_target target_name)
        if(TARGET ${target_name})
            get_target_property(TARGET_SOURCES ${target_name} SOURCES)
            if(TARGET_SOURCES)
                foreach(source_file ${TARGET_SOURCES})
                    if(source_file MATCHES "\\.(cpp|cc|cxx|c\\+\\+|hpp|hxx|h\\+\\+|h)$")
                        get_filename_component(source_file_abs ${source_file} ABSOLUTE)
                        add_custom_command(TARGET ${target_name}
                            PRE_BUILD
                            COMMAND ${CPPLINT_EXE} ${CPPLINT_ARGS} ${source_file_abs}
                            COMMENT "Running cpplint on ${source_file}"
                            VERBATIM
                        )
                    endif()
                endforeach()
            endif()
        endif()
    endfunction()

    # 创建独立的 cpplint 检查目标
    add_custom_target(cpplint
        COMMAND ${CMAKE_COMMAND} -E echo "Running cpplint on all source files..."
        COMMAND find ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/include
            -name "*.cpp" -o -name "*.hpp" -o -name "*.h" |
            xargs -I {} ${CPPLINT_EXE} ${CPPLINT_ARGS} {}
        COMMENT "Running cpplint style check"
        VERBATIM
    )

    message(STATUS "Cpplint integration enabled")
else()
    message(WARNING "cpplint not found. Install with: pip install cpplint")
endif()