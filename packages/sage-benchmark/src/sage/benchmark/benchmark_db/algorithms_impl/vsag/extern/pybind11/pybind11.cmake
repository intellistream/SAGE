include(FetchContent)

# Use local pybind11 from algorithms_impl directory
set(PYBIND11_LOCAL_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../../pybind11")
if(EXISTS "${PYBIND11_LOCAL_PATH}/CMakeLists.txt")
    message(STATUS "Using local pybind11 from: ${PYBIND11_LOCAL_PATH}")
    add_subdirectory(${PYBIND11_LOCAL_PATH} ${CMAKE_CURRENT_BINARY_DIR}/pybind11_local EXCLUDE_FROM_ALL)
else()
    message(STATUS "Local pybind11 not found, fetching from remote...")
    FetchContent_Declare(
            pybind11
            URL https://github.com/pybind/pybind11/archive/refs/tags/v2.11.1.tar.gz
                # this url is maintained by the vsag project, if it's broken, please try
                #  the latest commit or contact the vsag project
                http://vsagcache.oss-rg-china-mainland.aliyuncs.com/pybind11/v2.11.1.tar.gz
            URL_HASH MD5=49e92f92244021912a56935918c927d0
            DOWNLOAD_NO_PROGRESS 1
            INACTIVITY_TIMEOUT 5
            TIMEOUT 30
    )
    FetchContent_MakeAvailable(pybind11)
endif()
