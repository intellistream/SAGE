# Core Library
file(GLOB_RECURSE CORE_SOURCES "*.cpp")

if(CORE_SOURCES)
    add_library(sage_flow_core STATIC ${CORE_SOURCES})
else()
    # Create interface library if no sources found
    add_library(sage_flow_core INTERFACE)
endif()

target_include_directories(sage_flow_core INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
    $<INSTALL_INTERFACE:include>
)

if(CORE_SOURCES)
    target_link_libraries(sage_flow_core
        PRIVATE
            sage_flow_api
            sage_flow_common
            sage_flow_engine
            sage_flow_index
            sage_flow_function
            sage_flow_memory
            sage_flow_message
            sage_flow_operator
            sage_flow_sources
            sage_flow_environment
    )
endif()
