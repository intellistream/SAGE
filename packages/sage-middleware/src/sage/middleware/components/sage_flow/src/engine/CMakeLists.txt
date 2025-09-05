# Engine Library
# Include all engine sources except the basic stream_engine.cpp
# since enhanced_stream_engine.cpp provides the complete implementation
file(GLOB_RECURSE ENGINE_SOURCES "*.cpp")
# list(REMOVE_ITEM ENGINE_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/stream_engine.cpp")
add_library(sage_flow_engine STATIC ${ENGINE_SOURCES})

target_include_directories(sage_flow_engine PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
    $<INSTALL_INTERFACE:include>
)

# Add -fPIC for shared library compatibility
set_target_properties(sage_flow_engine PROPERTIES POSITION_INDEPENDENT_CODE ON)
