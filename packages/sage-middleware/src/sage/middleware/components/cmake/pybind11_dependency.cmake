# Shared pybind11 dependency resolver for SAGE C++ extensions
#
# Usage:
#   include("${CMAKE_CURRENT_SOURCE_DIR}/../cmake/pybind11_dependency.cmake")
#   # afterwards the function `pybind11_add_module` and targets `pybind11::module`
#   # will be available.
#
# Behaviour:
#   1. Prefer an existing pybind11 installation discoverable via find_package.
#   2. Fallback to FetchContent on a pinned, vetted version (v2.13.0).
#   3. Guarded so the FetchContent path only runs once per configure step.

if(NOT TARGET pybind11::module)
    find_package(pybind11 CONFIG QUIET)
    if(pybind11_FOUND)
        message(STATUS "Using system pybind11 ${pybind11_VERSION} from ${pybind11_CONFIG}")
    else()
        include(FetchContent)
        if(NOT DEFINED pybind11_POPULATED)
            set(_sage_pybind11_git_tag "v2.13.0" CACHE STRING "Pinned pybind11 version for SAGE extensions")
            FetchContent_Declare(
                pybind11
                GIT_REPOSITORY https://github.com/pybind/pybind11.git
                GIT_TAG ${_sage_pybind11_git_tag}
            )
        endif()
        FetchContent_MakeAvailable(pybind11)
        message(STATUS "Fetched pybind11 ${_sage_pybind11_git_tag} for SAGE extensions")
    endif()
endif()

if(NOT COMMAND pybind11_add_module)
    message(FATAL_ERROR "pybind11_add_module is unavailable even after resolving pybind11 dependency")
endif()
