# Sources Library
file(GLOB_RECURSE SOURCES_SOURCES "*.cpp")

if(SOURCES_SOURCES)
    add_library(sage_flow_sources STATIC ${SOURCES_SOURCES})

    target_include_directories(sage_flow_sources PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
        $<INSTALL_INTERFACE:include>
    )
else()
    message(STATUS "No sources source files found, skipping sage_flow_sources library")
endif()