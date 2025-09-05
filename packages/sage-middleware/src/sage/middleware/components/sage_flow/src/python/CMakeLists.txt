# Pybind11 Module - conditionally built
find_package(pybind11 QUIET)

if(pybind11_FOUND)
    message(STATUS "Found pybind11 - building Python bindings")

    file(GLOB_RECURSE PYTHON_SOURCES "*.cpp")
    pybind11_add_module(sage_flow_datastream ${PYTHON_SOURCES})

    # Use static linking to avoid GLIBCXX version issues
    target_link_libraries(sage_flow_datastream PRIVATE -static-libstdc++ -static-libgcc)

    target_link_libraries(sage_flow_datastream PRIVATE
        sage_flow_core
        sage_flow_common
        sage_flow_datastream_lib
        sage_flow_engine
        sage_flow_environment
        sage_flow_function
        sage_flow_index
        sage_flow_memory
        sage_flow_message
        sage_flow_operator
        sage_flow_sources
    )
else()
    message(WARNING "pybind11 not found - skipping Python bindings. Install pybind11 to enable Python support.")
endif()
