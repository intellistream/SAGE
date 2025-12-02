cmake_minimum_required(VERSION 3.14)
project(ipdiskann LANGUAGES CXX)

find_package(pybind11 REQUIRED)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

pybind11_add_module(ipdiskann MODULE
        index_wrapper.cpp
        pybind_module.cpp
)

set_target_properties(ipdiskann PROPERTIES
        PREFIX ""
        OUTPUT_NAME "ipdiskann"
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN YES
)

target_link_libraries(ipdiskann PRIVATE diskann)

install(TARGETS ipdiskann
        LIBRARY DESTINATION ${Python3_SITEARCH}   # Unix: .so
        RUNTIME DESTINATION ${Python3_SITEARCH}   # Windows: .pyd
        ARCHIVE DESTINATION ${Python3_SITEARCH}   # fallback
)
