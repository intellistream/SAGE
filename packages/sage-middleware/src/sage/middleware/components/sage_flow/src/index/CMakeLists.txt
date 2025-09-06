# Index Library
file(GLOB_RECURSE INDEX_SOURCES "*.cpp")
add_library(sage_flow_index STATIC ${INDEX_SOURCES})

target_include_directories(sage_flow_index PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
    $<INSTALL_INTERFACE:include>
)

# Link to memory library for memory pool functionality
target_link_libraries(sage_flow_index PUBLIC sage_flow_memory)

# Add -fPIC for shared library compatibility
set_target_properties(sage_flow_index PROPERTIES POSITION_INDEPENDENT_CODE ON)
