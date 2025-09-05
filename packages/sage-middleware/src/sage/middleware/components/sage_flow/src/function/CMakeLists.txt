# Function Library
file(GLOB_RECURSE FUNCTION_SOURCES "*.cpp")

if(FUNCTION_SOURCES)
    add_library(sage_flow_function STATIC ${FUNCTION_SOURCES})

    target_include_directories(sage_flow_function PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
        $<INSTALL_INTERFACE:include>
    )

    # Add -fPIC for shared library compatibility
    set_target_properties(sage_flow_function PROPERTIES POSITION_INDEPENDENT_CODE ON)
else()
    message(STATUS "No function source files found, skipping sage_flow_function library")
endif()