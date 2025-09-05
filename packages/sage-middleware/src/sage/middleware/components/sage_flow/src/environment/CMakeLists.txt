# Environment Library
file(GLOB_RECURSE ENVIRONMENT_SOURCES "*.cpp")

if(ENVIRONMENT_SOURCES)
    add_library(sage_flow_environment STATIC ${ENVIRONMENT_SOURCES})

    target_include_directories(sage_flow_environment PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
        $<INSTALL_INTERFACE:include>
    )

    # Add -fPIC for shared library compatibility
    set_target_properties(sage_flow_environment PROPERTIES POSITION_INDEPENDENT_CODE ON)
else()
    message(STATUS "No environment source files found, skipping sage_flow_environment library")
endif()