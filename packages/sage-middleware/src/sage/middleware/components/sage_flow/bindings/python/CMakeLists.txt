# Pybind11 Module - conditionally built
find_package(pybind11 QUIET)

if(pybind11_FOUND)
    message(STATUS "Found pybind11 - building Python bindings")

    file(GLOB_RECURSE PYTHON_SOURCES "*.cpp")
    pybind11_add_module(sageflow ${PYTHON_SOURCES})

    target_include_directories(sageflow PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../include>
        $<INSTALL_INTERFACE:include>
    )

    # Use static linking to avoid GLIBCXX version issues
    target_link_libraries(sageflow PRIVATE -static-libstdc++ -static-libgcc)

    target_link_libraries(sageflow PRIVATE
        sage_flow_datastream_lib
        sage_flow_engine
        sage_flow_environment
        sage_flow_function
        sage_flow_index
        sage_flow_memory
        sage_flow_message
        sage_flow_operator
        sage_flow_sources
        Python3::NumPy
    )
else()
    message(WARNING "pybind11 not found - skipping Python bindings. Install pybind11 to enable Python support.")
endif()
