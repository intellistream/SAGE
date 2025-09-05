# Memory Library
file(GLOB_RECURSE MEMORY_SOURCES "*.cpp")

if(MEMORY_SOURCES)
    add_library(sage_flow_memory STATIC ${MEMORY_SOURCES})

    target_include_directories(sage_flow_memory PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
        $<INSTALL_INTERFACE:include>
    )

    # Add -fPIC for shared library compatibility
    set_target_properties(sage_flow_memory PROPERTIES POSITION_INDEPENDENT_CODE ON)
else()
    message(STATUS "No memory source files found, skipping sage_flow_memory library")
endif()