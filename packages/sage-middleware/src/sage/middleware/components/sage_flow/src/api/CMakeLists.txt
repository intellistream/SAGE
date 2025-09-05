# API Library
file(GLOB_RECURSE API_SOURCES "*.cpp")

# Only create library if sources are found
if(API_SOURCES)
    add_library(sage_flow_api STATIC ${API_SOURCES})

    target_include_directories(sage_flow_api PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
        $<INSTALL_INTERFACE:include>
    )
else()
    message(STATUS "No API source files found, skipping sage_flow_api library")
endif()
