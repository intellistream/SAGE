cmake_minimum_required(VERSION 3.12)
project(sage_queue VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build options
option(BUILD_TESTS "Build test programs" ON)
option(BUILD_PYTHON_BINDINGS "Build Python bindings" ON)
option(USE_OPENMP "Enable OpenMP support" ON)
option(BUILD_DEBUG "Build with debug symbols and AddressSanitizer" OFF)

# Debug build configuration
if(BUILD_DEBUG)
    set(CMAKE_BUILD_TYPE Debug)
    set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -fsanitize=address -fno-omit-frame-pointer")
    message(STATUS "Building with debug symbols and AddressSanitizer")
else()
    set(CMAKE_BUILD_TYPE Release)
    set(CMAKE_CXX_FLAGS_RELEASE "-O2")
    message(STATUS "Building optimized release version")
endif()

# OpenMP support
if(USE_OPENMP)
    find_package(OpenMP)
    if(OpenMP_CXX_FOUND)
        message(STATUS "OpenMP found")
    endif()
endif()

# Find Boost
find_package(Boost REQUIRED)
if(Boost_FOUND)
    message(STATUS "Boost found: ${Boost_VERSION}")
    include_directories(${Boost_INCLUDE_DIRS})
else()
    message(FATAL_ERROR "Boost not found")
endif()

# Source files
set(SAGE_QUEUE_SOURCES
    src/simple_boost_queue.cpp
)

set(SAGE_QUEUE_HEADERS
    include/simple_boost_queue.h
    include/ring_buffer.h
    include/concurrentqueue.h
    include/lightweightsemaphore.h
)

# Include directories
include_directories(include)

# Create shared library
add_library(sage_queue SHARED ${SAGE_QUEUE_SOURCES})

# Set library properties
set_target_properties(sage_queue PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
    OUTPUT_NAME "ring_buffer"  # For compatibility with existing code
    POSITION_INDEPENDENT_CODE ON
)

# Link libraries
if(OpenMP_CXX_FOUND AND USE_OPENMP)
    target_link_libraries(sage_queue OpenMP::OpenMP_CXX)
endif()

# Link required libraries for Boost.Interprocess
target_link_libraries(sage_queue rt pthread)

# Compiler-specific options
target_compile_options(sage_queue PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra>
    $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra>
)

# Install targets
install(TARGETS sage_queue
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(FILES ${SAGE_QUEUE_HEADERS}
    DESTINATION include/sage_queue
)

# Create compatibility symlink (for existing code that expects ring_buffer.so)
install(CODE "
    execute_process(COMMAND \${CMAKE_COMMAND} -E create_symlink
        libring_buffer.so
        \${CMAKE_INSTALL_PREFIX}/lib/ring_buffer.so
    )
")

# Python bindings
if(BUILD_PYTHON_BINDINGS)
    # Find Python
    find_package(Python3 COMPONENTS Interpreter Development)
    
    if(Python3_FOUND)
        # Try to find pybind11
        find_package(pybind11 QUIET)
        
        if(pybind11_FOUND)
            message(STATUS "Found pybind11: ${pybind11_VERSION}")
            
            # Create Python module
            pybind11_add_module(sage_queue_bindings 
                bindings/sage_queue_bindings.cpp
            )
            
            target_link_libraries(sage_queue_bindings PRIVATE sage_queue)
            
            # Install Python module
            install(TARGETS sage_queue_bindings
                LIBRARY DESTINATION python/sage_queue
            )
        else()
            message(WARNING "pybind11 not found, skipping Python bindings")
        endif()
    else()
        message(WARNING "Python3 not found, skipping Python bindings")
    endif()
endif()

# Tests
if(BUILD_TESTS)
    enable_testing()
    
    # Simple test to verify library can be loaded
    add_executable(test_sage_queue tests/test_basic.cpp)
    target_link_libraries(test_sage_queue sage_queue)
    
    add_test(NAME test_sage_queue COMMAND test_sage_queue)
endif()

# Build information
message(STATUS "=== SAGE Queue Build Configuration ===")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build tests: ${BUILD_TESTS}")
message(STATUS "Build Python bindings: ${BUILD_PYTHON_BINDINGS}")
message(STATUS "Use OpenMP: ${USE_OPENMP}")
message(STATUS "Debug build: ${BUILD_DEBUG}")
if(OpenMP_CXX_FOUND AND USE_OPENMP)
    message(STATUS "OpenMP version: ${OpenMP_CXX_VERSION}")
endif()
message(STATUS "=====================================")
