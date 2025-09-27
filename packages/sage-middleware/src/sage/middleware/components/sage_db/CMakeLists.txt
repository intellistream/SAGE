cmake_minimum_required(VERSION 3.12)
project(sage_db VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build options
option(BUILD_TESTS "Build test programs" ON)
option(BUILD_PYTHON_BINDINGS "Build Python bindings" ON)
option(USE_OPENMP "Enable OpenMP support" ON)

# Find packages (keep minimal to improve portability)

# Add cmake modules directory to the path
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

# Use enhanced BLAS/LAPACK finder
include(FindBLASLAPACK)

# Try to find FAISS
find_path(FAISS_INCLUDE_DIR NAMES faiss/IndexFlat.h
    HINTS
    ${FAISS_ROOT}/include
    /usr/local/include
    /usr/include
    /opt/conda/include
    $ENV{CONDA_PREFIX}/include
)

find_library(FAISS_LIBRARY NAMES faiss
    HINTS
    ${FAISS_ROOT}/lib
    /usr/local/lib
    /usr/lib
    /opt/conda/lib
    $ENV{CONDA_PREFIX}/lib
)

if(FAISS_INCLUDE_DIR AND FAISS_LIBRARY)
    message(STATUS "Found FAISS: ${FAISS_LIBRARY}")
    set(FAISS_FOUND TRUE)
else()
    message(WARNING "FAISS not found, will install via conda in build script")
    set(FAISS_FOUND FALSE)
endif()

# OpenMP support
if(USE_OPENMP)
    find_package(OpenMP)
    if(OpenMP_CXX_FOUND)
        message(STATUS "OpenMP found")
    endif()
endif()

# Source files
set(SAGE_DB_SOURCES
    src/sage_db.cpp
    src/vector_store.cpp
    src/metadata_store.cpp
    src/query_engine.cpp
)

set(SAGE_DB_HEADERS
    include/sage_db/sage_db.h
    include/sage_db/vector_store.h
    include/sage_db/metadata_store.h
    include/sage_db/query_engine.h
    include/sage_db/common.h
)

# Create shared library
add_library(sage_db SHARED ${SAGE_DB_SOURCES})

# Include directories
target_include_directories(sage_db PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

if(FAISS_FOUND)
    target_include_directories(sage_db PRIVATE ${FAISS_INCLUDE_DIR})
    target_link_libraries(sage_db PRIVATE ${FAISS_LIBRARY})
    if(HAVE_BLAS_LAPACK)
        target_link_libraries(sage_db PRIVATE ${BLAS_LIBRARIES} ${LAPACK_LIBRARIES})
    endif()
    target_compile_definitions(sage_db PRIVATE FAISS_AVAILABLE)
endif()

# OpenMP linking
if(OpenMP_CXX_FOUND)
    target_link_libraries(sage_db PUBLIC OpenMP::OpenMP_CXX)
endif()

# Compiler specific options
target_compile_options(sage_db PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -O3>
    $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra -O3>
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /O2>
)

# Python bindings
if(BUILD_PYTHON_BINDINGS)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
    
    # Always download a newer pybind11 version that supports Python 3.11
    message(STATUS "Downloading pybind11 for Python 3.11 compatibility...")
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11
        GIT_TAG v2.13.0
    )
    FetchContent_MakeAvailable(pybind11)
    
    pybind11_add_module(_sage_db python/bindings.cpp)
    target_link_libraries(_sage_db PRIVATE sage_db)
    target_compile_definitions(_sage_db PRIVATE VERSION_INFO="${PROJECT_VERSION}")
    
    # 禁用 LTO 以避免链接器问题，设置输出属性
    set_target_properties(_sage_db PROPERTIES
        INTERPROCEDURAL_OPTIMIZATION OFF
        OUTPUT_NAME "_sage_db"
        PREFIX ""
    )
    
    # 在某些系统上，pybind11 默认启用 LTO，我们需要显式禁用
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        target_compile_options(_sage_db PRIVATE -fno-lto)
        target_link_options(_sage_db PRIVATE -fno-lto)
    endif()
endif()

# Tests
if(BUILD_TESTS)
    enable_testing()
    
    add_executable(test_sage_db tests/test_sage_db.cpp)
    target_link_libraries(test_sage_db PRIVATE sage_db)
    target_include_directories(test_sage_db PRIVATE include)
    
    add_test(NAME test_sage_db COMMAND test_sage_db)
endif()

# Install rules
install(TARGETS sage_db
    EXPORT sage_db_targets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include)

if(BUILD_PYTHON_BINDINGS)
    install(TARGETS _sage_db DESTINATION .)
endif()
