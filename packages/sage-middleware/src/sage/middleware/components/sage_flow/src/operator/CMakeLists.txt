# Operator Library
file(GLOB_RECURSE OPERATOR_SOURCES "*.cpp")

if(OPERATOR_SOURCES)
    add_library(sage_flow_operator STATIC ${OPERATOR_SOURCES})

    target_include_directories(sage_flow_operator PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
        $<INSTALL_INTERFACE:include>
    )

    # Add -fPIC for shared library compatibility
    set_target_properties(sage_flow_operator PROPERTIES POSITION_INDEPENDENT_CODE ON)
else()
    message(STATUS "No operator source files found, skipping sage_flow_operator library")
endif()