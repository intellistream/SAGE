# bindings/CMakeLists.txt
cmake_minimum_required(VERSION 3.10)
set(N2_LIB_PATH "${PROJECT_SOURCE_DIR}/extern_libraries/n2/build/lib")

# Force the use of the old ABI, consistent with the extern_libraries/n2 library.
add_definitions(-D_GLIBCXX_USE_CXX11_ABI=0)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)

if(NOT pybind11_FOUND)
    execute_process(
            COMMAND python -c "import pybind11; print(pybind11.get_cmake_dir())"
            OUTPUT_VARIABLE pybind11_DIR
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET
    )
    if(pybind11_DIR)
        find_package(pybind11 REQUIRED PATHS ${pybind11_DIR})
    else()
        message(FATAL_ERROR "pybind11 not found. Please install it with: pip install pybind11")
    endif()
endif()

find_package(OpenMP REQUIRED)
if(OPENMP_FOUND)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
else()
    message(FATAL_ERROR "OpenMP not found")
endif()

find_package(fmt REQUIRED)

include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(${PROJECT_SOURCE_DIR}/extern_libraries/n2/include)

link_directories(${PROJECT_SOURCE_DIR}/extern_libraries/n2/build/lib)

#pybind11_add_module(gti_wrapper gti_wrapper.cpp ../src/gti.cpp)
file(GLOB GTI_SRC_FILES "${PROJECT_SOURCE_DIR}/src/*.cpp")
pybind11_add_module(gti_wrapper gti_wrapper.cpp ${GTI_SRC_FILES})

target_compile_definitions(gti_wrapper PRIVATE VERSION_INFO=${EXAMPLE_VERSION_INFO})

target_link_libraries(gti_wrapper PRIVATE
#        gti_lib
        n2
        fmt::fmt
)

if(OPENMP_FOUND)
    target_link_libraries(gti_wrapper PRIVATE OpenMP::OpenMP_CXX)
endif()

target_compile_options(gti_wrapper PRIVATE -O3)

set_target_properties(gti_wrapper PROPERTIES
        PREFIX ""
        OUTPUT_NAME "gti_wrapper"
)

set_target_properties(gti_wrapper PROPERTIES
        INSTALL_RPATH "${N2_LIB_PATH}"
        BUILD_WITH_INSTALL_RPATH TRUE
)

install(TARGETS gti_wrapper
        LIBRARY DESTINATION ${Python3_SITEARCH})
