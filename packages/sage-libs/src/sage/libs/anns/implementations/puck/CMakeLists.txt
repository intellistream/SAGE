cmake_minimum_required(VERSION 3.21)

project(puck)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

set(THIRD_PARTY_PATH ${CMAKE_CURRENT_BINARY_DIR}/third_libs)
include_directories(PUBLIC "/usr/include/mkl")
# config GIT_URL with github mirrors to speed up dependent repos clone
option(GIT_URL "Git URL to clone dependent repos" ${GIT_URL})
if(NOT GIT_URL)
    set(GIT_URL "https://github.com")
endif()


set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_FLAGS "-std=c++14 -w -g0 -Ofast -fPIC")
set(CMAKE_C_FLAGS "-std=c++14 -w -g0 -Ofast -fPIC")
#add_definitions(-D_GLIBCXX_USE_CXX11_ABI=0)
add_definitions(-DFINTEGER=int)

add_compile_options(-fopenmp -lpthread -lcrypto -lrt -lgfortran -ldl -lz -fPIC -rdynamic)
add_compile_options(-Ofast -g -pipe -fPIC -march=native -w)

#include(${PROJECT_SOURCE_DIR}/cmake/gflags.cmake)
#include(${PROJECT_SOURCE_DIR}/cmake/glog.cmake)
#set(CMAKE_PREFIX_PATH "/usr/local/lib" ${CMAKE_PREFIX_PATH})
find_package(OpenMP REQUIRED)
find_package(MKL REQUIRED)


set(CMAKE_INSTALL_PREFIX ${CMAKE_BINARY_DIR}/output)
#add_subdirectory(pyapi_wrapper)
add_subdirectory(puck)

set(PYTHON_MINIMUM_VERSION 3.10)




# find python3
find_package(Python3 ${PYTHON_MINIMUM_VERSION} REQUIRED COMPONENTS Interpreter Development)
message(STATUS "Found Python: ${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}.${Python3_VERSION_PATCH}")
if (NOT Python3_SITELIB)
    message(FATAL_ERROR "site-packages not found. ")
else ()
    message(STATUS "site-packages: ${Python3_SITELIB}")
endif ()

#add_subdirectory(test)


#
