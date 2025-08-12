# Python C++ 项目规范

## 目录
- [概述](#概述)
- [项目结构标准](#项目结构标准)
- [C++ 扩展开发规范](#c-扩展开发规范)
- [构建系统集成](#构建系统集成)
- [接口设计原则](#接口设计原则)
- [性能优化策略](#性能优化策略)
- [测试和调试](#测试和调试)
- [部署和分发](#部署和分发)
- [最佳实践](#最佳实践)

## 概述

Python C++ 混合项目是现代高性能应用开发的重要模式，特别在以下领域：

- **科学计算**: NumPy, SciPy, Pandas
- **机器学习**: PyTorch, TensorFlow, XGBoost  
- **数据处理**: Apache Arrow, Polars
- **图形计算**: OpenCV, VTK

SAGE 项目采用现代化的 Python C++ 集成标准，提供高性能扩展的同时保持 Python 的开发便利性。

### 技术栈选择

```
Python 层
├── pybind11 (Python ↔ C++ 绑定)
├── NumPy C API (数组操作)
└── setuptools (构建集成)

C++ 层  
├── C++17/20 (现代 C++ 标准)
├── CMake (构建系统)
├── OpenMP (并行计算)
└── 第三方库 (Eigen, OpenBLAS, etc.)
```

## 项目结构标准

### SAGE 项目的 C++ 扩展结构

```
packages/sage-extensions/
├── pyproject.toml              # Python 项目配置
├── setup.py                    # 构建脚本
├── CMakeLists.txt              # 顶层 CMake 配置
├── README.md                   # 文档
├── LICENSE                     # 许可证
│
├── src/sage/extensions/        # Python 包结构
│   ├── __init__.py
│   ├── sage_db/               # 数据库扩展
│   │   ├── __init__.py
│   │   ├── core.py            # Python 接口
│   │   ├── CMakeLists.txt     # CMake 配置
│   │   ├── src/               # C++ 源码
│   │   │   ├── database.cpp
│   │   │   ├── database.hpp
│   │   │   ├── bindings.cpp   # pybind11 绑定
│   │   │   └── utils.hpp
│   │   └── include/           # 公共头文件
│   │       └── sage_db/
│   │           └── database.hpp
│   │
│   └── sage_queue/            # 队列扩展
│       ├── __init__.py
│       ├── core.py
│       ├── CMakeLists.txt
│       └── src/
│           ├── queue.cpp
│           ├── queue.hpp
│           └── bindings.cpp
│
├── tests/                     # 测试
│   ├── test_sage_db.py
│   ├── test_sage_queue.py
│   └── cpp_tests/            # C++ 单元测试
│       ├── CMakeLists.txt
│       ├── test_database.cpp
│       └── test_queue.cpp
│
├── benchmarks/               # 性能测试
│   ├── benchmark_db.py
│   └── benchmark_queue.py
│
├── scripts/                  # 构建脚本
│   ├── build.py             # 主构建脚本
│   ├── install_deps.sh      # 系统依赖安装
│   └── test.py              # 测试脚本
│
└── docs/                    # 文档
    ├── api.md
    ├── development.md
    └── performance.md
```

### 目录结构设计原则

#### 1. Python 包命名空间

```python
# 遵循 Python 包结构
sage/
├── extensions/           # 扩展命名空间
│   ├── sage_db/         # 具体扩展包
│   │   ├── __init__.py  # Python 接口
│   │   └── core.py      # 高级 API
│   └── sage_queue/
│       ├── __init__.py
│       └── core.py

# 使用方式
from sage.extensions.sage_db import Database
from sage.extensions.sage_queue import Queue
```

#### 2. C++ 源码组织

```cpp
// 头文件命名空间组织
// include/sage_db/database.hpp
#pragma once

namespace sage {
namespace db {
    class Database {
        // 实现
    };
}
}

// 源文件组织
// src/database.cpp
#include "sage_db/database.hpp"
namespace sage::db {
    // 实现
}
```

#### 3. CMake 模块化

```cmake
# 顶层 CMakeLists.txt
cmake_minimum_required(VERSION 3.18)
project(sage_extensions)

# 查找依赖
find_package(pybind11 REQUIRED)
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# 添加子模块
add_subdirectory(src/sage/extensions/sage_db)
add_subdirectory(src/sage/extensions/sage_queue)

# 测试
if(BUILD_TESTING)
    add_subdirectory(tests/cpp_tests)
endif()
```

## C++ 扩展开发规范

### 1. 代码风格和标准

#### C++ 版本和特性

```cpp
// 使用现代 C++ 特性
#include <memory>
#include <vector>
#include <string_view>
#include <optional>

// 推荐：使用 C++17/20 特性
class Database {
public:
    // 使用智能指针
    std::unique_ptr<Connection> connection_;
    
    // 使用 string_view 避免不必要的拷贝
    bool execute(std::string_view query);
    
    // 使用 optional 表示可能失败的操作
    std::optional<ResultSet> select(std::string_view query);
    
    // 使用 auto 和范围 for
    void process_results(const std::vector<Row>& rows) {
        for (const auto& row : rows) {
            // 处理每一行
        }
    }
};
```

#### 命名规范

```cpp
// 类名：PascalCase
class DatabaseConnection {};

// 函数名：snake_case
void execute_query();

// 变量名：snake_case
std::string connection_string;

// 常量：UPPER_SNAKE_CASE
const int MAX_CONNECTIONS = 100;

// 私有成员：trailing underscore
class Database {
private:
    std::string connection_string_;
    int max_connections_;
};

// 命名空间：snake_case
namespace sage::db::internal {
    // 内部实现
}
```

### 2. pybind11 绑定规范

#### 基本绑定模式

```cpp
// bindings.cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>           // STL 容器支持
#include <pybind11/numpy.h>         // NumPy 支持
#include <pybind11/eigen.h>         // Eigen 支持
#include "sage_db/database.hpp"

namespace py = pybind11;

PYBIND11_MODULE(sage_db, m) {
    m.doc() = "SAGE Database Extension";
    
    // 绑定类
    py::class_<sage::db::Database>(m, "Database")
        .def(py::init<const std::string&>(),
             py::arg("connection_string"),
             "Create database connection")
        
        .def("execute", &sage::db::Database::execute,
             py::arg("query"),
             "Execute SQL query")
        
        .def("select", &sage::db::Database::select,
             py::arg("query"),
             "Execute SELECT query and return results")
        
        // 属性访问
        .def_property_readonly("is_connected", 
                              &sage::db::Database::is_connected)
        
        // Python 上下文管理器支持
        .def("__enter__", [](sage::db::Database& self) -> sage::db::Database& {
            return self;
        })
        .def("__exit__", [](sage::db::Database& self, py::object, py::object, py::object) {
            self.close();
        });
    
    // 绑定异常
    py::register_exception<sage::db::DatabaseError>(m, "DatabaseError");
    
    // 绑定枚举
    py::enum_<sage::db::QueryType>(m, "QueryType")
        .value("SELECT", sage::db::QueryType::SELECT)
        .value("INSERT", sage::db::QueryType::INSERT)
        .value("UPDATE", sage::db::QueryType::UPDATE)
        .value("DELETE", sage::db::QueryType::DELETE);
}
```

#### NumPy 集成

```cpp
#include <pybind11/numpy.h>

// 使用 NumPy 数组作为参数
void process_array(py::array_t<double> input) {
    // 获取缓冲区信息
    auto buf = input.request();
    
    // 检查维度
    if (buf.ndim != 2) {
        throw std::runtime_error("Input array must be 2-dimensional");
    }
    
    // 访问数据
    double* ptr = static_cast<double*>(buf.ptr);
    size_t rows = buf.shape[0];
    size_t cols = buf.shape[1];
    
    // 处理数据
    for (size_t i = 0; i < rows; ++i) {
        for (size_t j = 0; j < cols; ++j) {
            ptr[i * cols + j] *= 2.0;  // 示例操作
        }
    }
}

// 返回 NumPy 数组
py::array_t<double> create_array(size_t rows, size_t cols) {
    // 创建数组
    auto result = py::array_t<double>(
        py::buffer_info(
            nullptr,            // 数据指针（稍后分配）
            sizeof(double),     // 元素大小
            py::format_descriptor<double>::format(), // 格式
            2,                  // 维度数
            {rows, cols},       // 形状
            {sizeof(double) * cols, sizeof(double)} // 步长
        )
    );
    
    // 获取缓冲区并初始化
    auto buf = result.request();
    double* ptr = static_cast<double*>(buf.ptr);
    
    for (size_t i = 0; i < rows * cols; ++i) {
        ptr[i] = static_cast<double>(i);
    }
    
    return result;
}
```

### 3. 错误处理和异常

#### C++ 异常设计

```cpp
// sage_db/exceptions.hpp
#pragma once
#include <stdexcept>
#include <string>

namespace sage::db {
    
    // 基础数据库异常
    class DatabaseError : public std::runtime_error {
    public:
        explicit DatabaseError(const std::string& message)
            : std::runtime_error(message) {}
    };
    
    // 连接异常
    class ConnectionError : public DatabaseError {
    public:
        explicit ConnectionError(const std::string& message)
            : DatabaseError("Connection error: " + message) {}
    };
    
    // 查询异常
    class QueryError : public DatabaseError {
    private:
        std::string query_;
        
    public:
        QueryError(const std::string& message, const std::string& query)
            : DatabaseError("Query error: " + message)
            , query_(query) {}
        
        const std::string& query() const { return query_; }
    };
}
```

#### Python 异常绑定

```cpp
// bindings.cpp
PYBIND11_MODULE(sage_db, m) {
    // 注册异常类型
    py::register_exception<sage::db::DatabaseError>(m, "DatabaseError", PyExc_RuntimeError);
    py::register_exception<sage::db::ConnectionError>(m, "ConnectionError", PyExc_ConnectionError);
    
    // 自定义异常转换
    py::register_exception_translator([](std::exception_ptr p) {
        try {
            if (p) std::rethrow_exception(p);
        } catch (const sage::db::QueryError& e) {
            // 创建包含查询信息的 Python 异常
            py::dict details;
            details["query"] = e.query();
            details["message"] = e.what();
            PyErr_SetObject(PyExc_RuntimeError, details.ptr());
        }
    });
}
```

## 构建系统集成

### 1. CMake 配置

#### 顶层 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.18)
project(sage_extensions LANGUAGES CXX)

# C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 构建类型
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# 编译选项
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    add_compile_options(-Wall -Wextra -O3 -march=native)
endif()

# 查找依赖
find_package(pybind11 REQUIRED)
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(PkgConfig REQUIRED)

# OpenMP 支持
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
endif()

# 全局包含目录
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# 添加子模块
add_subdirectory(src/sage/extensions/sage_db)
add_subdirectory(src/sage/extensions/sage_queue)

# 测试
option(BUILD_TESTS "Build tests" OFF)
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests/cpp_tests)
endif()
```

#### 模块级 CMakeLists.txt

```cmake
# src/sage/extensions/sage_db/CMakeLists.txt

# 收集源文件
file(GLOB_RECURSE SAGE_DB_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.hpp"
)

# 创建 pybind11 模块
pybind11_add_module(sage_db ${SAGE_DB_SOURCES})

# 编译定义
target_compile_definitions(sage_db PRIVATE VERSION_INFO=${EXAMPLE_VERSION_INFO})

# 链接库
target_link_libraries(sage_db PRIVATE 
    ${BLAS_LIBRARIES}
    ${LAPACK_LIBRARIES}
)

# OpenMP 支持
if(OpenMP_CXX_FOUND)
    target_link_libraries(sage_db PRIVATE OpenMP::OpenMP_CXX)
endif()

# 包含目录
target_include_directories(sage_db PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${PYTHON_INCLUDE_DIRS}
)

# 安装配置
install(TARGETS sage_db DESTINATION .)
```

### 2. 构建脚本集成

#### Python 构建脚本

```python
# scripts/build.py
#!/usr/bin/env python3
"""
SAGE Extensions 构建脚本
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import multiprocessing

class ExtensionBuilder:
    def __init__(self, source_dir=None, build_dir=None):
        self.source_dir = Path(source_dir or Path(__file__).parent.parent)
        self.build_dir = Path(build_dir or self.source_dir / "build")
        self.parallel_jobs = os.environ.get('PARALLEL_JOBS', 
                                          str(multiprocessing.cpu_count()))
    
    def check_dependencies(self):
        """检查构建依赖"""
        required_tools = ['cmake', 'gcc', 'pkg-config']
        missing = []
        
        for tool in required_tools:
            if not shutil.which(tool):
                missing.append(tool)
        
        if missing:
            raise RuntimeError(f"Missing required tools: {missing}")
        
        # 检查 Python 开发头文件
        try:
            import pybind11
            print(f"✅ pybind11 {pybind11.__version__} found")
        except ImportError:
            print("Installing pybind11...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pybind11'])
    
    def configure(self, build_type='Release'):
        """配置构建"""
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        cmake_args = [
            'cmake',
            f'-DCMAKE_BUILD_TYPE={build_type}',
            f'-DPYTHON_EXECUTABLE={sys.executable}',
            '-DBUILD_TESTS=ON',
            str(self.source_dir)
        ]
        
        # GPU 支持
        if self._has_cuda():
            cmake_args.append('-DWITH_GPU=ON')
        
        # 执行配置
        subprocess.run(cmake_args, cwd=self.build_dir, check=True)
    
    def build(self):
        """执行构建"""
        build_args = [
            'cmake', '--build', str(self.build_dir),
            '--config', 'Release',
            '--', f'-j{self.parallel_jobs}'
        ]
        
        subprocess.run(build_args, check=True)
    
    def install(self):
        """安装扩展"""
        # 查找生成的 .so 文件
        so_files = list(self.build_dir.glob('**/*.so'))
        
        # 安装到源码目录
        for so_file in so_files:
            # 确定目标位置
            if 'sage_db' in str(so_file):
                target_dir = self.source_dir / 'src/sage/extensions/sage_db'
            elif 'sage_queue' in str(so_file):
                target_dir = self.source_dir / 'src/sage/extensions/sage_queue'
            else:
                continue
            
            target_file = target_dir / so_file.name
            shutil.copy2(so_file, target_file)
            print(f"✅ Installed {so_file.name} to {target_file}")
    
    def test(self):
        """运行测试"""
        # C++ 测试
        test_dir = self.build_dir / 'tests/cpp_tests'
        if test_dir.exists():
            subprocess.run(['ctest', '--output-on-failure'], 
                         cwd=self.build_dir, check=True)
        
        # Python 测试
        subprocess.run([sys.executable, '-m', 'pytest', 'tests/'], 
                      cwd=self.source_dir, check=True)
    
    def _has_cuda(self):
        """检查 CUDA 支持"""
        return shutil.which('nvcc') is not None

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build SAGE extensions')
    parser.add_argument('--build-type', default='Release', 
                       choices=['Debug', 'Release'])
    parser.add_argument('--clean', action='store_true', 
                       help='Clean before building')
    parser.add_argument('--test', action='store_true', 
                       help='Run tests after building')
    
    args = parser.parse_args()
    
    builder = ExtensionBuilder()
    
    try:
        if args.clean and builder.build_dir.exists():
            shutil.rmtree(builder.build_dir)
        
        print("🔍 Checking dependencies...")
        builder.check_dependencies()
        
        print("⚙️ Configuring build...")
        builder.configure(args.build_type)
        
        print("🔨 Building extensions...")
        builder.build()
        
        print("📦 Installing extensions...")
        builder.install()
        
        if args.test:
            print("🧪 Running tests...")
            builder.test()
        
        print("✅ Build completed successfully!")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## 接口设计原则

### 1. Python 风格的 API 设计

#### 数据库扩展示例

```python
# sage/extensions/sage_db/__init__.py
"""
SAGE Database Extension

高性能数据库操作扩展，提供：
- 快速 SQL 查询执行
- 批量数据处理
- 内存优化的结果集
- 异步操作支持
"""

from .sage_db import Database as _Database, DatabaseError, QueryType
from typing import Optional, List, Dict, Any, Union, Iterator
import asyncio

class Database:
    """高级数据库接口"""
    
    def __init__(self, connection_string: str, **kwargs):
        """
        创建数据库连接
        
        Args:
            connection_string: 数据库连接字符串
            **kwargs: 其他连接参数
        """
        self._db = _Database(connection_string)
        self._connection_params = kwargs
    
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行 SQL 查询
        
        Args:
            query: SQL 查询语句
            params: 查询参数
            
        Returns:
            影响的行数
            
        Raises:
            DatabaseError: 查询执行失败
        """
        try:
            if params:
                # 参数化查询
                return self._db.execute_with_params(query, params)
            return self._db.execute(query)
        except Exception as e:
            raise DatabaseError(f"Query execution failed: {e}") from e
    
    def select(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行 SELECT 查询
        
        Args:
            query: SELECT 查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        return self._db.select(query, params or {})
    
    def select_iter(self, query: str, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """
        流式查询，适合大数据集
        
        Args:
            query: SELECT 查询语句  
            batch_size: 批次大小
            
        Yields:
            批次结果
        """
        offset = 0
        while True:
            batch_query = f"{query} LIMIT {batch_size} OFFSET {offset}"
            results = self.select(batch_query)
            
            if not results:
                break
                
            yield results
            offset += batch_size
    
    async def execute_async(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """异步执行查询"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, query, params)
    
    def __enter__(self):
        """上下文管理器支持"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """清理资源"""
        self.close()
    
    def close(self):
        """关闭连接"""
        self._db.close()

# 便利函数
def connect(connection_string: str, **kwargs) -> Database:
    """创建数据库连接的便利函数"""
    return Database(connection_string, **kwargs)
```

### 2. 类型提示和文档

```python
# sage/extensions/sage_db/types.py
"""类型定义"""

from typing import TypedDict, Literal, Union, Any
from enum import Enum

class QueryType(Enum):
    """查询类型枚举"""
    SELECT = "SELECT"
    INSERT = "INSERT" 
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class ConnectionConfig(TypedDict, total=False):
    """连接配置类型"""
    host: str
    port: int
    database: str
    username: str
    password: str
    timeout: int
    pool_size: int

Row = Dict[str, Any]
ResultSet = List[Row]
QueryParams = Dict[str, Union[str, int, float, bool, None]]
```

## 性能优化策略

### 1. 内存管理优化

#### 零拷贝数据传输

```cpp
// 使用 NumPy 缓冲区协议实现零拷贝
class DatabaseResult {
private:
    std::vector<double> data_;
    std::vector<size_t> shape_;
    
public:
    // 返回 NumPy 数组视图，避免拷贝
    py::array_t<double> as_numpy_array() {
        return py::array_t<double>(
            shape_,
            {sizeof(double) * shape_[1], sizeof(double)}, // 步长
            data_.data(),                                  // 数据指针
            py::cast(*this)                               // 保持对象存活
        );
    }
};
```

#### 对象池模式

```cpp
template<typename T>
class ObjectPool {
private:
    std::queue<std::unique_ptr<T>> pool_;
    std::mutex mutex_;
    
public:
    std::unique_ptr<T> acquire() {
        std::lock_guard<std::mutex> lock(mutex_);
        
        if (pool_.empty()) {
            return std::make_unique<T>();
        }
        
        auto obj = std::move(pool_.front());
        pool_.pop();
        return obj;
    }
    
    void release(std::unique_ptr<T> obj) {
        obj->reset();  // 重置对象状态
        
        std::lock_guard<std::mutex> lock(mutex_);
        pool_.push(std::move(obj));
    }
};
```

### 2. 并行计算优化

#### OpenMP 集成

```cpp
#include <omp.h>

void parallel_matrix_multiply(
    const py::array_t<double>& a,
    const py::array_t<double>& b,
    py::array_t<double>& result) {
    
    auto buf_a = a.request();
    auto buf_b = b.request();
    auto buf_result = result.request();
    
    double* ptr_a = static_cast<double*>(buf_a.ptr);
    double* ptr_b = static_cast<double*>(buf_b.ptr);
    double* ptr_result = static_cast<double*>(buf_result.ptr);
    
    int rows_a = buf_a.shape[0];
    int cols_a = buf_a.shape[1];
    int cols_b = buf_b.shape[1];
    
    #pragma omp parallel for collapse(2)
    for (int i = 0; i < rows_a; ++i) {
        for (int j = 0; j < cols_b; ++j) {
            double sum = 0.0;
            for (int k = 0; k < cols_a; ++k) {
                sum += ptr_a[i * cols_a + k] * ptr_b[k * cols_b + j];
            }
            ptr_result[i * cols_b + j] = sum;
        }
    }
}
```

#### 异步操作支持

```cpp
#include <future>
#include <thread>

class AsyncDatabase {
private:
    std::thread worker_thread_;
    std::queue<std::function<void()>> task_queue_;
    std::mutex queue_mutex_;
    std::condition_variable cv_;
    bool stop_flag_ = false;
    
public:
    AsyncDatabase() : worker_thread_(&AsyncDatabase::worker_loop, this) {}
    
    ~AsyncDatabase() {
        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            stop_flag_ = true;
        }
        cv_.notify_all();
        worker_thread_.join();
    }
    
    std::future<ResultSet> select_async(const std::string& query) {
        auto promise = std::make_shared<std::promise<ResultSet>>();
        auto future = promise->get_future();
        
        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            task_queue_.push([this, query, promise]() {
                try {
                    auto result = this->select_sync(query);
                    promise->set_value(result);
                } catch (...) {
                    promise->set_exception(std::current_exception());
                }
            });
        }
        
        cv_.notify_one();
        return future;
    }
    
private:
    void worker_loop() {
        while (true) {
            std::function<void()> task;
            
            {
                std::unique_lock<std::mutex> lock(queue_mutex_);
                cv_.wait(lock, [this] { return !task_queue_.empty() || stop_flag_; });
                
                if (stop_flag_ && task_queue_.empty()) {
                    break;
                }
                
                task = std::move(task_queue_.front());
                task_queue_.pop();
            }
            
            task();
        }
    }
};
```

## 测试和调试

### 1. C++ 单元测试

```cpp
// tests/cpp_tests/test_database.cpp
#include <gtest/gtest.h>
#include "sage_db/database.hpp"

class DatabaseTest : public ::testing::Test {
protected:
    void SetUp() override {
        db_ = std::make_unique<sage::db::Database>(":memory:");
    }
    
    void TearDown() override {
        db_.reset();
    }
    
    std::unique_ptr<sage::db::Database> db_;
};

TEST_F(DatabaseTest, BasicConnection) {
    EXPECT_TRUE(db_->is_connected());
}

TEST_F(DatabaseTest, QueryExecution) {
    const std::string create_table = R"(
        CREATE TABLE test (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    )";
    
    EXPECT_NO_THROW(db_->execute(create_table));
    
    const std::string insert_data = R"(
        INSERT INTO test (name) VALUES ('Alice'), ('Bob')
    )";
    
    int affected_rows = db_->execute(insert_data);
    EXPECT_EQ(affected_rows, 2);
}

TEST_F(DatabaseTest, SelectQuery) {
    // 准备测试数据
    db_->execute("CREATE TABLE users (id INTEGER, name TEXT)");
    db_->execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')");
    
    // 执行查询
    auto results = db_->select("SELECT * FROM users ORDER BY id");
    
    // 验证结果
    ASSERT_EQ(results.size(), 2);
    EXPECT_EQ(results[0]["id"], 1);
    EXPECT_EQ(results[0]["name"], "Alice");
    EXPECT_EQ(results[1]["id"], 2);
    EXPECT_EQ(results[1]["name"], "Bob");
}

// 性能测试
TEST_F(DatabaseTest, PerformanceBenchmark) {
    // 创建大量数据
    db_->execute("CREATE TABLE benchmark (id INTEGER, value REAL)");
    
    const int num_records = 100000;
    auto start = std::chrono::high_resolution_clock::now();
    
    // 批量插入
    db_->execute("BEGIN TRANSACTION");
    for (int i = 0; i < num_records; ++i) {
        db_->execute("INSERT INTO benchmark VALUES (?, ?)", {i, i * 0.5});
    }
    db_->execute("COMMIT");
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    std::cout << "Inserted " << num_records << " records in " 
              << duration.count() << " ms" << std::endl;
    
    // 性能应该在合理范围内
    EXPECT_LT(duration.count(), 5000);  // 应该在 5 秒内完成
}
```

### 2. Python 集成测试

```python
# tests/test_sage_db.py
import pytest
import numpy as np
from sage.extensions.sage_db import Database, DatabaseError

class TestDatabase:
    @pytest.fixture
    def db(self):
        """测试数据库实例"""
        with Database(":memory:") as db:
            yield db
    
    def test_basic_operations(self, db):
        """测试基本操作"""
        # 创建表
        db.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL
            )
        """)
        
        # 插入数据
        affected = db.execute("""
            INSERT INTO test_table (name, value) 
            VALUES ('test1', 1.5), ('test2', 2.5)
        """)
        assert affected == 2
        
        # 查询数据
        results = db.select("SELECT * FROM test_table ORDER BY id")
        assert len(results) == 2
        assert results[0]['name'] == 'test1'
        assert results[0]['value'] == 1.5
    
    def test_parameterized_query(self, db):
        """测试参数化查询"""
        db.execute("CREATE TABLE users (id INTEGER, name TEXT, age INTEGER)")
        
        # 参数化插入
        db.execute(
            "INSERT INTO users (name, age) VALUES (?, ?)",
            {"name": "Alice", "age": 25}
        )
        
        # 参数化查询
        results = db.select(
            "SELECT * FROM users WHERE age > ?",
            {"age": 20}
        )
        
        assert len(results) == 1
        assert results[0]['name'] == 'Alice'
    
    def test_numpy_integration(self, db):
        """测试 NumPy 集成"""
        # 创建测试数据
        data = np.random.random((1000, 3))
        
        # 批量插入（假设有相应的方法）
        db.bulk_insert_array("test_array", data, columns=['x', 'y', 'z'])
        
        # 查询并返回 NumPy 数组
        result_array = db.select_as_array("SELECT x, y, z FROM test_array")
        
        assert isinstance(result_array, np.ndarray)
        assert result_array.shape == (1000, 3)
        np.testing.assert_array_almost_equal(result_array, data)
    
    def test_error_handling(self, db):
        """测试错误处理"""
        # 语法错误
        with pytest.raises(DatabaseError, match="syntax error"):
            db.execute("INVALID SQL SYNTAX")
        
        # 表不存在
        with pytest.raises(DatabaseError, match="no such table"):
            db.select("SELECT * FROM nonexistent_table")
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with Database(":memory:") as db:
            db.execute("CREATE TABLE test (id INTEGER)")
            db.execute("INSERT INTO test VALUES (1)")
            
            results = db.select("SELECT * FROM test")
            assert len(results) == 1
        
        # 连接应该已经关闭
        assert not db.is_connected()
    
    @pytest.mark.asyncio
    async def test_async_operations(self, db):
        """测试异步操作"""
        db.execute("CREATE TABLE async_test (id INTEGER)")
        
        # 异步插入
        affected = await db.execute_async("INSERT INTO async_test VALUES (1)")
        assert affected == 1
        
        # 异步查询
        results = await db.select_async("SELECT * FROM async_test")
        assert len(results) == 1

# 性能测试
class TestPerformance:
    def test_bulk_insert_performance(self):
        """测试批量插入性能"""
        with Database(":memory:") as db:
            db.execute("CREATE TABLE perf_test (id INTEGER, value REAL)")
            
            import time
            start_time = time.time()
            
            # 批量插入
            num_records = 100000
            db.bulk_insert(
                "perf_test",
                [(i, i * 0.5) for i in range(num_records)]
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Inserted {num_records} records in {duration:.2f} seconds")
            print(f"Rate: {num_records/duration:.0f} records/second")
            
            # 验证数据
            count = db.select("SELECT COUNT(*) as count FROM perf_test")[0]['count']
            assert count == num_records
```

### 3. 调试工具

#### 内存泄漏检测

```cpp
// debug/memory_tracker.hpp
#pragma once
#include <unordered_map>
#include <mutex>
#include <iostream>

class MemoryTracker {
private:
    static std::unordered_map<void*, size_t> allocations_;
    static std::mutex mutex_;
    static size_t total_allocated_;
    
public:
    static void* allocate(size_t size) {
        void* ptr = malloc(size);
        
        std::lock_guard<std::mutex> lock(mutex_);
        allocations_[ptr] = size;
        total_allocated_ += size;
        
        return ptr;
    }
    
    static void deallocate(void* ptr) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = allocations_.find(ptr);
        if (it != allocations_.end()) {
            total_allocated_ -= it->second;
            allocations_.erase(it);
        }
        
        free(ptr);
    }
    
    static void report() {
        std::lock_guard<std::mutex> lock(mutex_);
        
        std::cout << "Memory Report:\n";
        std::cout << "Total allocated: " << total_allocated_ << " bytes\n";
        std::cout << "Active allocations: " << allocations_.size() << "\n";
        
        if (!allocations_.empty()) {
            std::cout << "Potential leaks:\n";
            for (const auto& [ptr, size] : allocations_) {
                std::cout << "  " << ptr << ": " << size << " bytes\n";
            }
        }
    }
};

// 使用宏替换标准分配函数
#ifdef DEBUG_MEMORY
#define malloc(size) MemoryTracker::allocate(size)
#define free(ptr) MemoryTracker::deallocate(ptr)
#endif
```

## 部署和分发

### 1. 跨平台构建

#### 构建脚本优化

```python
# scripts/cross_platform_build.py
import platform
import subprocess
import sys
from pathlib import Path

class CrossPlatformBuilder:
    def __init__(self):
        self.system = platform.system().lower()
        self.architecture = platform.machine().lower()
        
    def install_system_deps(self):
        """安装系统依赖"""
        if self.system == 'linux':
            self._install_linux_deps()
        elif self.system == 'darwin':
            self._install_macos_deps()
        elif self.system == 'windows':
            self._install_windows_deps()
    
    def _install_linux_deps(self):
        """Linux 依赖安装"""
        distro = self._detect_linux_distro()
        
        if distro in ['ubuntu', 'debian']:
            subprocess.run([
                'sudo', 'apt-get', 'update', '&&',
                'sudo', 'apt-get', 'install', '-y',
                'build-essential', 'cmake', 'pkg-config',
                'libblas-dev', 'liblapack-dev', 'libomp-dev'
            ], shell=True)
        
        elif distro in ['centos', 'rhel', 'fedora']:
            subprocess.run([
                'sudo', 'yum', 'install', '-y',
                'gcc-c++', 'cmake', 'pkgconfig',
                'blas-devel', 'lapack-devel', 'libomp-devel'
            ])
    
    def _install_macos_deps(self):
        """macOS 依赖安装"""
        subprocess.run([
            'brew', 'install', 
            'cmake', 'gcc', 'pkg-config', 'openblas', 'libomp'
        ])
    
    def _install_windows_deps(self):
        """Windows 依赖安装"""
        # 使用 vcpkg 或提供预编译库
        print("Please install Visual Studio Build Tools and vcpkg")
        print("Then run: vcpkg install cmake:x64-windows")
    
    def configure_cmake(self):
        """配置 CMake"""
        cmake_args = [
            '-DCMAKE_BUILD_TYPE=Release',
            f'-DPYTHON_EXECUTABLE={sys.executable}',
        ]
        
        # 平台特定配置
        if self.system == 'darwin':
            cmake_args.extend([
                '-DCMAKE_OSX_DEPLOYMENT_TARGET=10.14',
                '-DCMAKE_CXX_COMPILER=clang++',
            ])
        elif self.system == 'windows':
            cmake_args.extend([
                '-G', 'Visual Studio 16 2019',
                '-A', 'x64',
            ])
        
        return cmake_args
```

### 2. Wheel 打包

#### setup.py 中的 Wheel 配置

```python
# setup.py
from setuptools import setup
from wheel.bdist_wheel import bdist_wheel

class BdistWheel(bdist_wheel):
    """自定义 wheel 构建"""
    
    def finalize_options(self):
        # 强制平台特定的 wheel
        self.universal = False
        super().finalize_options()
    
    def get_tag(self):
        # 获取平台标签
        python_tag, abi_tag, platform_tag = super().get_tag()
        
        # 确保 ABI 标签正确
        if abi_tag == 'none':
            abi_tag = 'abi3'  # 稳定 ABI
        
        return python_tag, abi_tag, platform_tag

setup(
    cmdclass={
        'build_ext': BuildExtCommand,
        'install': CustomInstallCommand,
        'bdist_wheel': BdistWheel,
    }
)
```

#### CI/CD 多平台构建

```yaml
# .github/workflows/build-wheels.yml
name: Build Wheels

on: [push, pull_request]

jobs:
  build_wheels:
    name: Build wheels on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-20.04, windows-2019, macos-11]
        python: [3.8, 3.9, '3.10', 3.11]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python }}
    
    - name: Install system dependencies
      run: |
        if [ "$RUNNER_OS" == "Linux" ]; then
          sudo apt-get update
          sudo apt-get install -y build-essential cmake libblas-dev liblapack-dev
        elif [ "$RUNNER_OS" == "macOS" ]; then
          brew install cmake gcc openblas
        fi
      shell: bash
    
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build wheel pybind11[global] numpy
    
    - name: Build wheel
      run: |
        cd packages/sage-extensions
        python -m build --wheel
    
    - name: Test wheel
      run: |
        pip install packages/sage-extensions/dist/*.whl
        python -c "import sage.extensions.sage_db; print('✅ Import successful')"
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: wheels-${{ matrix.os }}-py${{ matrix.python }}
        path: packages/sage-extensions/dist/*.whl
```

## 最佳实践

### 1. 项目组织最佳实践

#### 模块化设计

```
sage-extensions/
├── src/sage/extensions/
│   ├── common/              # 公共组件
│   │   ├── memory_pool.hpp  # 内存池
│   │   ├── thread_pool.hpp  # 线程池
│   │   └── utils.hpp        # 工具函数
│   │
│   ├── sage_db/            # 数据库模块
│   │   ├── core/           # 核心功能
│   │   ├── drivers/        # 数据库驱动
│   │   └── bindings/       # Python 绑定
│   │
│   └── sage_queue/         # 队列模块
│       ├── core/
│       ├── algorithms/
│       └── bindings/
```

#### 版本管理策略

```cpp
// version.hpp - 编译时版本信息
#pragma once

#define SAGE_EXTENSIONS_VERSION_MAJOR 1
#define SAGE_EXTENSIONS_VERSION_MINOR 0
#define SAGE_EXTENSIONS_VERSION_PATCH 0

#define SAGE_EXTENSIONS_VERSION \
    ((SAGE_EXTENSIONS_VERSION_MAJOR << 16) | \
     (SAGE_EXTENSIONS_VERSION_MINOR << 8) | \
     SAGE_EXTENSIONS_VERSION_PATCH)

namespace sage {
    const char* get_version_string();
    int get_version_number();
}
```

```python
# __init__.py - 运行时版本检查
import sys
from .sage_db import get_version_string, get_version_number

__version__ = "1.0.0"

def check_version_compatibility():
    """检查 C++ 扩展版本兼容性"""
    cpp_version = get_version_string()
    if not cpp_version.startswith(__version__.split('.')[0]):
        raise RuntimeError(
            f"Version mismatch: Python package {__version__}, "
            f"C++ extension {cpp_version}"
        )

# 导入时自动检查
check_version_compatibility()
```

### 2. 性能监控和调优

#### 性能分析工具集成

```cpp
// profiling/profiler.hpp
#pragma once
#include <chrono>
#include <string>
#include <unordered_map>

class Profiler {
private:
    static std::unordered_map<std::string, double> timings_;
    
public:
    class Timer {
    private:
        std::string name_;
        std::chrono::high_resolution_clock::time_point start_;
        
    public:
        Timer(const std::string& name) : name_(name) {
            start_ = std::chrono::high_resolution_clock::now();
        }
        
        ~Timer() {
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration<double>(end - start_).count();
            Profiler::add_timing(name_, duration);
        }
    };
    
    static void add_timing(const std::string& name, double seconds);
    static void report();
    static void clear();
};

// 便利宏
#define PROFILE_SCOPE(name) Profiler::Timer _timer(name)
#define PROFILE_FUNCTION() PROFILE_SCOPE(__FUNCTION__)
```

#### 内存使用监控

```python
# monitoring/memory_monitor.py
import psutil
import time
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class MemorySnapshot:
    timestamp: float
    rss_mb: float          # 物理内存
    vms_mb: float          # 虚拟内存
    percent: float         # 内存使用百分比
    available_mb: float    # 可用内存

class MemoryMonitor:
    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.process = psutil.Process()
    
    def take_snapshot(self) -> MemorySnapshot:
        """获取内存快照"""
        memory_info = self.process.memory_info()
        system_memory = psutil.virtual_memory()
        
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=self.process.memory_percent(),
            available_mb=system_memory.available / 1024 / 1024
        )
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def get_peak_memory(self) -> float:
        """获取峰值内存使用"""
        if not self.snapshots:
            return 0.0
        return max(s.rss_mb for s in self.snapshots)
    
    def get_memory_trend(self) -> Dict[str, float]:
        """获取内存使用趋势"""
        if len(self.snapshots) < 2:
            return {"trend": 0.0, "rate": 0.0}
        
        first = self.snapshots[0]
        last = self.snapshots[-1]
        
        time_diff = last.timestamp - first.timestamp
        memory_diff = last.rss_mb - first.rss_mb
        
        return {
            "trend": memory_diff,
            "rate": memory_diff / time_diff if time_diff > 0 else 0.0
        }

# 使用示例
def benchmark_with_monitoring():
    monitor = MemoryMonitor()
    
    # 基准测试
    from sage.extensions.sage_db import Database
    
    with Database(":memory:") as db:
        monitor.take_snapshot()  # 初始快照
        
        # 大量数据操作
        db.execute("CREATE TABLE test (id INTEGER, data TEXT)")
        
        for i in range(100000):
            db.execute(f"INSERT INTO test VALUES ({i}, 'data_{i}')")
            
            if i % 10000 == 0:
                monitor.take_snapshot()
        
        # 查询操作
        results = db.select("SELECT * FROM test LIMIT 1000")
        monitor.take_snapshot()
    
    # 分析结果
    peak_memory = monitor.get_peak_memory()
    trend = monitor.get_memory_trend()
    
    print(f"Peak memory usage: {peak_memory:.2f} MB")
    print(f"Memory trend: {trend['trend']:+.2f} MB")
    print(f"Memory rate: {trend['rate']:+.2f} MB/s")
```

### 3. 文档和示例

#### API 文档生成

```python
# docs/generate_api_docs.py
"""
自动生成 API 文档
"""

import inspect
import pybind11_stubgen
from pathlib import Path

def generate_stubs():
    """生成类型存根文件"""
    pybind11_stubgen.main([
        "sage.extensions.sage_db",
        "sage.extensions.sage_queue", 
        "--output-dir", "stubs",
        "--ignore-invalid-expressions",
    ])

def generate_examples():
    """生成示例代码"""
    examples = {
        "basic_usage.py": """
# 基本使用示例
from sage.extensions.sage_db import Database

# 创建连接
with Database("example.db") as db:
    # 创建表
    db.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        )
    ''')
    
    # 插入数据
    db.execute("INSERT INTO users (name, email) VALUES (?, ?)", 
               ("Alice", "alice@example.com"))
    
    # 查询数据
    users = db.select("SELECT * FROM users")
    for user in users:
        print(f"User: {user['name']} <{user['email']}>")
""",
        
        "performance_example.py": """
# 性能优化示例
import numpy as np
from sage.extensions.sage_db import Database

# 大数据量处理
with Database(":memory:") as db:
    # 批量插入
    data = np.random.random((1000000, 3))
    db.bulk_insert_array("measurements", data, 
                         columns=["x", "y", "z"])
    
    # 流式查询
    for batch in db.select_iter("SELECT * FROM measurements", 
                                batch_size=10000):
        # 处理每个批次
        batch_array = np.array([[row['x'], row['y'], row['z']] 
                               for row in batch])
        # 执行计算...
""",
    }
    
    examples_dir = Path("docs/examples")
    examples_dir.mkdir(exist_ok=True)
    
    for filename, content in examples.items():
        (examples_dir / filename).write_text(content)

if __name__ == "__main__":
    generate_stubs()
    generate_examples()
```

## 总结

Python C++ 项目规范为 SAGE 这样的高性能应用提供了：

1. **标准化项目结构**: 清晰的模块组织和文件布局
2. **现代化工具链**: pybind11, CMake, setuptools 的完美集成
3. **性能优化策略**: 内存管理、并行计算、零拷贝等技术
4. **完整的测试框架**: C++ 和 Python 的测试覆盖
5. **跨平台支持**: 统一的构建和部署流程

这些规范确保了：
- **开发效率**: 简化的构建流程和调试工具
- **代码质量**: 严格的类型检查和测试要求
- **性能表现**: 针对性的优化策略和监控
- **维护性**: 清晰的文档和示例代码

下一章：[构建系统最佳实践](./build_system_best_practices.md) →
