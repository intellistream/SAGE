# Common Library
file(GLOB_RECURSE COMMON_SOURCES "*.cpp")

if(COMMON_SOURCES)
    add_library(sage_flow_common STATIC ${COMMON_SOURCES})
else()
    # Create interface library if no sources found
    add_library(sage_flow_common INTERFACE)
endif()

target_include_directories(sage_flow_common INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
    $<INSTALL_INTERFACE:include>
)
