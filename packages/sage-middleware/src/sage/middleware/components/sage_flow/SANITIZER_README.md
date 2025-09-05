# SAGE Flow Sanitizer 配置指南

本文档介绍如何在SAGE Flow项目中使用各种sanitizer进行代码质量检查和调试。

## 📋 概述

项目集成了以下sanitizer：
- **AddressSanitizer (ASan)**: 检测内存错误
- **MemorySanitizer (MSan)**: 检测未初始化内存访问
- **ThreadSanitizer (TSan)**: 检测数据竞争
- **UndefinedBehaviorSanitizer (UBSan)**: 检测未定义行为
- **LeakSanitizer (LSan)**: 检测内存泄漏

## ⚙️ 快速开始

### 1. 启用Sanitizer

#### 方法1: CMake配置
```bash
# 开发配置 (推荐用于日常开发)
mkdir build && cd build
cmake .. -DSAGE_SANITIZER_ADDRESS=ON \
         -DSAGE_SANITIZER_UNDEFINED=ON \
         -DSAGE_SANITIZER_LEAK=ON \
         -DSAGE_SANITIZER_VERBOSE=ON

# 生产配置
cmake .. -DSAGE_SANITIZER_ADDRESS=ON \
         -DSAGE_SANITIZER_UNDEFINED=ON \
         -DSAGE_SANITIZER_LEVEL=minimal

# 测试配置
cmake .. -DSAGE_SANITIZER_ADDRESS=ON \
         -DSAGE_SANITIZER_UNDEFINED=ON \
         -DSAGE_SANITIZER_THREAD=ON \
         -DSAGE_SANITIZER_LEVEL=aggressive
```

#### 方法2: 使用脚本
```bash
# 使用预定义配置
./scripts/run_with_sanitizers.sh -c dev -b ./my_program

# 直接运行现有程序
./scripts/run_with_sanitizers.sh -c asan ./build/my_program
```

### 2. 构建项目
```bash
cd build
make -j$(nproc)
```

## 🛠️ 可用配置

### 预定义配置

| 配置 | 说明 | 适用场景 |
|------|------|----------|
| `dev` | Address + Undefined + Leak | 日常开发调试 |
| `prod` | Address + Undefined (最小级别) | 生产环境监控 |
| `test` | Address + Undefined + Thread | 全面测试 |
| `asan` | 仅 AddressSanitizer | 内存错误调试 |
| `tsan` | 仅 ThreadSanitizer | 并发问题调试 |
| `msan` | 仅 MemorySanitizer | 未初始化内存调试 |
| `ubsan` | 仅 UndefinedBehaviorSanitizer | 未定义行为调试 |

### 详细选项

```cmake
# 启用特定sanitizer
option(SAGE_SANITIZER_ADDRESS "Enable AddressSanitizer" OFF)
option(SAGE_SANITIZER_MEMORY "Enable MemorySanitizer" OFF)
option(SAGE_SANITIZER_THREAD "Enable ThreadSanitizer" OFF)
option(SAGE_SANITIZER_UNDEFINED "Enable UndefinedBehaviorSanitizer" OFF)
option(SAGE_SANITIZER_LEAK "Enable LeakSanitizer" OFF)

# 级别设置
set(SAGE_SANITIZER_LEVEL "medium" CACHE STRING "Sanitizer level")
# minimal, medium, aggressive, comprehensive

# 高级选项
option(SAGE_SANITIZER_VERBOSE "Enable verbose output" OFF)
option(SAGE_SANITIZER_STACK_TRACE "Enable stack traces" ON)
option(SAGE_SANITIZER_ENABLE_TESTS "Enable sanitizers for tests" ON)
```

## 🔍 Sanitizer功能详解

### AddressSanitizer (ASan)

检测以下内存错误：
- 堆缓冲区溢出/下溢出
- 栈缓冲区溢出
- 全局缓冲区溢出
- 使用已释放内存
- 释放已释放内存
- 内存泄漏

**示例输出:**
```
==29713==ERROR: AddressSanitizer: heap-use-after-free on address 0x502000000010
READ of size 4 at 0x502000000010 thread T0
    #0 0x57da6991d763 in test_use_after_free() test.cpp:32
    #1 0x57da6991dd29 in main test.cpp:82
```

### ThreadSanitizer (TSan)

检测数据竞争和并发问题：
- 数据竞争
- 死锁
- 原子操作问题
- 条件变量误用

### MemorySanitizer (MSan)

检测未初始化内存访问：
- 使用未初始化的局部变量
- 使用未初始化的堆内存
- 未初始化的参数传递

### UndefinedBehaviorSanitizer (UBSan)

检测未定义行为：
- 整数溢出
- 空指针解引用
- 无效的类型转换
- 数组越界
- 除零操作

### LeakSanitizer (LSan)

检测内存泄漏：
- 直接内存泄漏
- 间接内存泄漏
- 仍然可达的内存

## 🚀 运行和调试

### 环境变量配置

```bash
# AddressSanitizer
export ASAN_OPTIONS="verbosity=1:debug=1:detect_leaks=1"

# ThreadSanitizer
export TSAN_OPTIONS="verbosity=1:history_size=7"

# MemorySanitizer
export MSAN_OPTIONS="verbosity=1"

# UndefinedBehaviorSanitizer
export UBSAN_OPTIONS="verbosity=1:print_stacktrace=1"
```

### 常见使用场景

#### 1. 调试内存错误
```bash
# 启用AddressSanitizer
./scripts/run_with_sanitizers.sh -c asan ./my_program

# 详细输出
ASAN_OPTIONS="verbosity=1:debug=1" ./my_program
```

#### 2. 检测数据竞争
```bash
# 启用ThreadSanitizer
./scripts/run_with_sanitizers.sh -c tsan ./my_multithreaded_program
```

#### 3. CI/CD集成
```yaml
# GitHub Actions示例
- name: Build with sanitizers
  run: |
    mkdir build && cd build
    cmake .. -DSAGE_SANITIZER_ADDRESS=ON -DSAGE_SANITIZER_UNDEFINED=ON
    make

- name: Run tests with sanitizers
  run: |
    cd build
    ASAN_OPTIONS="abort_on_error=0" ctest
```

## ⚠️ 注意事项

### 冲突检测
某些sanitizer不能同时启用：
- AddressSanitizer 与 MemorySanitizer 冲突
- ThreadSanitizer 与 MemorySanitizer 冲突

系统会自动检测并报告冲突。

### 性能影响
- AddressSanitizer: ~2x 内存使用，~2x 执行时间
- ThreadSanitizer: ~5-15x 执行时间，~5-10x 内存使用
- MemorySanitizer: ~3x 内存使用

### 编译器要求
- AddressSanitizer: GCC 4.8+, Clang 3.1+
- ThreadSanitizer: GCC 7+, Clang 6+
- MemorySanitizer: Clang 3.1+ (GCC不支持)
- UndefinedBehaviorSanitizer: GCC 4.9+, Clang 3.3+

## 🔧 故障排除

### 常见问题

#### 1. 拦截失败警告
```
AddressSanitizer: failed to intercept 'malloc'
```
**解决:** 确保在main函数前初始化sanitizer，或使用静态链接。

#### 2. 误报处理
- 使用suppressions文件过滤已知误报
- 自动生成: `lsan.supp`

#### 3. 性能问题
- 在生产中使用`minimal`级别
- 禁用详细输出: `SAGE_SANITIZER_VERBOSE=OFF`

### 调试技巧

#### 1. 获取更多信息
```bash
# 启用详细输出
export ASAN_OPTIONS="verbosity=1:debug=1"

# 显示调用栈
export ASAN_OPTIONS="fast_unwind_on_malloc=0"
```

#### 2. 过滤特定错误
```bash
# 只显示错误，不显示警告
export ASAN_OPTIONS="halt_on_error=1"

# 继续执行不终止程序
export ASAN_OPTIONS="abort_on_error=0"
```

## 📚 相关资源

- [AddressSanitizer文档](https://clang.llvm.org/docs/AddressSanitizer.html)
- [ThreadSanitizer文档](https://clang.llvm.org/docs/ThreadSanitizer.html)
- [MemorySanitizer文档](https://clang.llvm.org/docs/MemorySanitizer.html)
- [UndefinedBehaviorSanitizer文档](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)

---

*最后更新: 2024年*