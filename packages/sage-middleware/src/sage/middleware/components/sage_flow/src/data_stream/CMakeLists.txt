# DataStream Library
file(GLOB_RECURSE DATASTREAM_SOURCES "*.cpp")

if(DATASTREAM_SOURCES)
    add_library(sage_flow_datastream_lib STATIC ${DATASTREAM_SOURCES})

    target_include_directories(sage_flow_datastream_lib PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
        $<INSTALL_INTERFACE:include>
    )

    # Add -fPIC for shared library compatibility
    set_target_properties(sage_flow_datastream_lib PROPERTIES POSITION_INDEPENDENT_CODE ON)
else()
    message(STATUS "No datastream source files found, skipping sage_flow_datastream_lib library")
endif()