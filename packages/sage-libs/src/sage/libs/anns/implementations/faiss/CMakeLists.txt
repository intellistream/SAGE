# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# =============================================================================
# Copyright (c) 2023, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.
# =============================================================================

cmake_minimum_required(VERSION 3.10 FATAL_ERROR)

set(FAISS_LANGUAGES CXX)

if(FAISS_ENABLE_GPU)
  list(APPEND FAISS_LANGUAGES CUDA)
endif()

if(FAISS_ENABLE_RAFT)
include(cmake/thirdparty/fetch_rapids.cmake)
include(rapids-cmake)
include(rapids-cpm)
include(rapids-cuda)
include(rapids-export)
include(rapids-find)

rapids_cuda_init_architectures(faiss)
rapids_cuda_init_architectures(pyfaiss)
rapids_cuda_init_architectures(faiss_c_library)
endif()

project(faiss
  VERSION 1.7.4
  DESCRIPTION "A library for efficient similarity search and clustering of dense vectors."
  HOMEPAGE_URL "https://github.com/facebookresearch/faiss"
  LANGUAGES ${FAISS_LANGUAGES})
include(GNUInstallDirs)

set(CMAKE_CXX_STANDARD 17)

list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

# Valid values are "generic", "avx2", "avx512".

# Define the function to detect AVX-512 support
function(detect_avx512_support result_var)
    include(CheckCXXSourceCompiles)
    set(CMAKE_REQUIRED_FLAGS "-mavx512f")
    check_cxx_source_compiles("
    #include <immintrin.h>
    int main() {
        __m512i vec = _mm512_set1_epi32(1);  // AVX-512 intrinsic
        return 0;
    }
" HAVE_AVX512)

    if(HAVE_AVX512)
        #message(STATUS "AVX-512 support detected.")
        set(${result_var} 1 PARENT_SCOPE)
    else()
       # message(STATUS "AVX-512 support NOT detected.")
        set(${result_var} 0 PARENT_SCOPE)
    endif()
endfunction()

function(detect_avx2_support result_var)
    include(CheckCXXSourceCompiles)
    # Save the current compiler flags to restore them later
    set(saved_flags "${CMAKE_CXX_FLAGS}")
    # Test AVX2 intrinsic support by compiling a minimal test program
    check_cxx_source_compiles("
        #include <immintrin.h>
        int main() {
            __m256i vec = _mm256_set1_epi32(1);  // AVX2 intrinsic
            return 0;
        }
    " HAVE_AVX2)

    # Restore the original compiler flags
    set(CMAKE_CXX_FLAGS "${saved_flags}" PARENT_SCOPE)
    # Return TRUE or FALSE based on the test result
    if(HAVE_AVX2)
        set(${result_var} 1 PARENT_SCOPE)
    else()
        set(${result_var} 0 PARENT_SCOPE)
    endif()
endfunction()

detect_avx512_support(AVX512_AVAILABLE)
# Use AVX-512 based on the result
if(AVX512_AVAILABLE)
    message(STATUS "AVX-512 support detected.")
    option(FAISS_OPT_LEVEL "" "avx512")
else()
    message(STATUS "AVX-512 support NOT detected.")
    detect_avx2_support(AVX2_AVAILABLE)
    if(AVX2_AVAILABLE)
        message(STATUS "AVX-2 support detected.")
        option(FAISS_OPT_LEVEL "" "avx2")
    else ()
        message(STATUS "AVX-2 support not detected.")
        option(FAISS_OPT_LEVEL "" "generic")
    endif ()
endif()



option(FAISS_ENABLE_GPU "Enable support for GPU indexes." OFF)
option(FAISS_ENABLE_RAFT "Enable RAFT for GPU indexes." OFF)
option(FAISS_ENABLE_PYTHON "Build Python extension." OFF)
option(FAISS_ENABLE_C_API "Build C API." OFF)

if(FAISS_ENABLE_GPU)
  set(CMAKE_CUDA_HOST_COMPILER ${CMAKE_CXX_COMPILER})
  enable_language(CUDA)
endif()

if(FAISS_ENABLE_RAFT)
  find_package(raft COMPONENTS compiled distributed)
endif()

add_subdirectory(faiss)

if(FAISS_ENABLE_GPU)
  add_subdirectory(faiss/gpu)
endif()

if(FAISS_ENABLE_PYTHON)
  #add_subdirectory(faiss/python)
endif()

if(FAISS_ENABLE_C_API)
  #add_subdirectory(c_api)
endif()

#add_subdirectory(demos)
#add_subdirectory(benchs)
#add_subdirectory(tutorial/cpp)

# CTest must be included in the top level to enable `make test` target.
include(CTest)
if(BUILD_TESTING)
 # add_subdirectory(tests)

  if(FAISS_ENABLE_GPU)
    #add_subdirectory(faiss/gpu/test)
  endif()
endif()
