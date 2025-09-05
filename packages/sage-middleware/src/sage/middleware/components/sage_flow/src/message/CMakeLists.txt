# Message Library
file(GLOB_RECURSE MESSAGE_SOURCES "*.cpp")

if(MESSAGE_SOURCES)
    add_library(sage_flow_message STATIC ${MESSAGE_SOURCES})

    target_include_directories(sage_flow_message PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
        $<INSTALL_INTERFACE:include>
    )

    # Add -fPIC for shared library compatibility
    set_target_properties(sage_flow_message PROPERTIES POSITION_INDEPENDENT_CODE ON)
else()
    message(STATUS "No message source files found, skipping sage_flow_message library")
endif()