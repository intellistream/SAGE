cmake_minimum_required(VERSION 3.16)
project(sage_flow VERSION 1.0.0 LANGUAGES CXX)

# C++17标准强制要求
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Google C++ Style编译选项
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  add_compile_options(
    -Wall -Wextra -Werror        # 警告即错误
    -Wshadow -Wconversion        # 额外警告
    -Wno-unused-parameter        # 允许未使用参数
  )
endif()

# clang-tidy集成
find_program(CLANG_TIDY_EXE NAMES "clang-tidy")
if(CLANG_TIDY_EXE)
  set(CMAKE_CXX_CLANG_TIDY 
    ${CLANG_TIDY_EXE};
    -config-file=${CMAKE_SOURCE_DIR}/.clang-tidy;
    -header-filter=.*
  )
endif()

# 包含目录
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# 查找依赖
find_package(pybind11 REQUIRED)

# 核心库源文件
set(SAGE_FLOW_SOURCES
  src/message/vector_data.cpp
  src/message/retrieval_context.cpp
  src/message/multimodal_message_core.cpp
  src/operator/operator.cpp
  src/function/text_processing.cpp
  src/index/index_operators.cpp
)

# 目标库定义
add_library(sage_flow_core SHARED ${SAGE_FLOW_SOURCES})

target_include_directories(sage_flow_core
  PUBLIC 
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# C++17标准
target_compile_features(sage_flow_core PUBLIC cxx_std_17)

# pybind11绑定模块
pybind11_add_module(sage_flow_py 
  src/python/bindings.cpp
)

target_link_libraries(sage_flow_py PRIVATE sage_flow_core)

# 安装规则
install(TARGETS sage_flow_core
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY include/
  DESTINATION include
  FILES_MATCHING PATTERN "*.h"
)
