cmake_minimum_required(VERSION 3.10)
project(GTI LANGUAGES CXX)

# Force the use of the old ABI, consistent with the extern_libraries/n2 library.
add_definitions(-D_GLIBCXX_USE_CXX11_ABI=0)

set(CMAKE_BUILD_TYPE Release)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(EXECUTABLE_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/bin)

# OpenMP
find_package(OpenMP REQUIRED)
if(OPENMP_FOUND)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
else()
    message(FATAL_ERROR "OpenMP not found")
endif()

# fmt
find_package(fmt REQUIRED)

# include dirs
include_directories(include)
include_directories(${PROJECT_SOURCE_DIR}/extern_libraries/n2/include)
include_directories(/usr/include/spdlog/include) # if need

# link dir for n2.so
link_directories(${PROJECT_SOURCE_DIR}/extern_libraries/n2/build/lib)

# add src Subdirectory
add_subdirectory(src)
add_subdirectory(bindings)
