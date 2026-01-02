# PAPI 预编译包解决方案

## 问题分析

当前 LibAMM 的 PAPI 集成存在以下问题：

1. **自行编译 PAPI**：通过 `thirdparty/installPAPI.sh` 脚本从源码编译 PAPI
1. **编译失败常见**：PAPI 编译依赖内核头文件、硬件架构，容易失败
1. **增加构建时间**：PAPI 编译需要额外 5-10 分钟
1. **维护负担**：需要维护 PAPI 源码和编译脚本

## 解决方案：使用系统预编译 PAPI

### 方案 1：完全禁用 PAPI（推荐用于大多数场景）

**优点**：

- ✅ 零依赖、零编译问题
- ✅ 构建速度最快
- ✅ 适合 99% 的用户场景

**实现方式**：

修改 `packages/sage-libs/src/sage/libs/amms/implementations/CMakeLists.txt`：

```cmake
option (ENABLE_PAPI
        "Enable papi support, pls first compile papi or set REBUILD_PAPI to ON"
        OFF  # 默认禁用
        )
```

修改 `packages/sage-libs/src/sage/libs/amms/implementations/setup.py`：

```python
# 注释掉 PAPI 编译和启用选项
# os.system("cd thirdparty&&./makeClean.sh&&./installPAPI.sh")
cmake_args = [
    # ...
    # "-DENABLE_PAPI=ON",  # 注释掉
]
```

修改构建脚本：

```bash
# buildCPUOnly.sh
cd build &&cmake ... -DENABLE_PAPI=OFF ...  # 改为 OFF

# buildWithCuda.sh  
cd build &&cmake ... -DENABLE_PAPI=OFF ...  # 改为 OFF
```

### 方案 2：使用系统预编译 PAPI（推荐用于需要性能分析的场景）

**优点**：

- ✅ 无需从源码编译
- ✅ 系统包管理器自动处理依赖
- ✅ 稳定、经过测试的版本
- ✅ 支持硬件性能计数器

**安装预编译 PAPI**：

```bash
# Ubuntu/Debian
sudo apt-get install libpapi-dev libpapi7.1t64

# CentOS/RHEL
sudo yum install papi-devel

# Fedora
sudo dnf install papi-devel
```

**修改 CMakeLists.txt 使用系统 PAPI**：

```cmake
option (ENABLE_PAPI
        "Enable papi support using system-installed libpapi"
        OFF
        )

# OPTIONAL PAPI
if (NOT ENABLE_PAPI)
    message(STATUS "I will NOT use PAPI ")
    set(LibAMM_PAPI 0)
else ()
    set(LibAMM_PAPI 1)
    message(STATUS "I will try to use PAPI for HW counters, pls make sure your arch supports it")

    # 移除 REBUILD_PAPI 选项，直接使用系统 PAPI
    # option (REBUILD_PAPI ...)  # 删除

    # 使用 CMake 标准方式查找系统 PAPI
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(PAPI REQUIRED papi)

    if (PAPI_FOUND)
        message(STATUS "Found system PAPI: ${PAPI_LIBRARIES}")
        message(STATUS "PAPI include dirs: ${PAPI_INCLUDE_DIRS}")
        include_directories(${PAPI_INCLUDE_DIRS})
        set(LIBRARIES ${LIBRARIES} ${PAPI_LIBRARIES})
    else()
        # Fallback: 直接查找库文件
        find_library(libPAPI NAMES papi libpapi.so PATHS /usr/lib /usr/local/lib)
        if (libPAPI)
            message(STATUS "Found PAPI library: ${libPAPI}")
            set(LIBRARIES ${LIBRARIES} ${libPAPI})
        else()
            message(FATAL_ERROR "ENABLE_PAPI is ON but libpapi not found. Install with: sudo apt-get install libpapi-dev")
        endif()
    endif()
endif ()
```

**修改 setup.py**：

```python
# 移除 PAPI 编译步骤
# os.system("cd thirdparty&&./makeClean.sh&&./installPAPI.sh")

cmake_args = [
    "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" + extdir,
    "-DPYTHON_EXECUTABLE=" + sys.executable,
    "-DCMAKE_PREFIX_PATH=" + torchCmake,
    "-DENABLE_HDF5=ON",
    "-DENABLE_PYBIND=ON",
    "-DCMAKE_INSTALL_PREFIX=/usr/local/lib",
    "-DENABLE_PAPI=OFF",  # 默认禁用，用户可手动启用
]

# 添加环境变量支持
if os.environ.get("ENABLE_PAPI") == "1":
    # 检查系统是否安装了 libpapi-dev
    import subprocess
    result = subprocess.run(["pkg-config", "--exists", "papi"], capture_output=True)
    if result.returncode == 0:
        cmake_args.append("-DENABLE_PAPI=ON")
        print("✓ Enabling PAPI support (system libpapi detected)")
    else:
        print("⚠ ENABLE_PAPI=1 but libpapi-dev not found. Install with:")
        print("  sudo apt-get install libpapi-dev")
        print("Continuing without PAPI...")
```

## 推荐方案：分层实现

### isage-amms 包（默认禁用 PAPI）

```python
# setup.py - 生产版本
cmake_args = [
    # ...
    "-DENABLE_PAPI=OFF",  # 默认禁用
]
```

### benchmark_amm 包（可选启用 PAPI）

在 `benchmark_amm/INSTALLATION.md` 中添加文档：

````markdown
## 可选：启用 PAPI 性能计数器

PAPI (Performance API) 用于硬件性能分析，大多数用户不需要。

### 如果需要 PAPI：

1. 安装系统 PAPI 包：
   ```bash
   sudo apt-get install libpapi-dev
````

2. 从源码构建 isage-amms（启用 PAPI）：

   ```bash
   git clone https://github.com/intellistream/SAGE.git
   cd SAGE/packages/sage-libs
   ENABLE_PAPI=1 pip install -e .
   ```

1. 验证 PAPI 支持：

   ```bash
   python -c "from sage.libs.amms import create_amm_index; print('PAPI enabled')"
   ```

### 注意事项：

- PAPI 需要硬件支持和内核配置
- 某些虚拟化环境可能不支持
- 如果编译失败，使用默认配置（不影响功能）

````

## 实施步骤

### 第一阶段：默认禁用 PAPI（立即实施）

1. ✅ 修改 `CMakeLists.txt`：`ENABLE_PAPI` 默认为 `OFF`
2. ✅ 修改 `setup.py`：注释掉 PAPI 编译和启用
3. ✅ 修改构建脚本：`buildCPUOnly.sh`, `buildWithCuda.sh` 设为 `OFF`
4. ✅ 更新文档：说明 PAPI 为可选功能

### 第二阶段：添加系统 PAPI 支持（可选）

1. ⏭️ 实现 CMake 的 `find_package(PAPI)` 逻辑
2. ⏭️ 添加环境变量 `ENABLE_PAPI=1` 支持
3. ⏭️ 更新 INSTALLATION.md 文档

## 优先级建议

**高优先级（立即执行）**：
- ✅ 默认禁用 PAPI（解决编译失败问题）
- ✅ 更新文档说明 PAPI 为可选

**低优先级（按需实施）**：
- ⏭️ 实现系统 PAPI 支持（如果用户需要性能分析）
- ⏭️ 添加自动检测逻辑

## 测试计划

### 测试场景 1：默认构建（无 PAPI）

```bash
cd packages/sage-libs
pip install -e .
python -c "from sage.libs.amms import create_amm_index; print('OK')"
````

预期：✅ 成功编译，无 PAPI 依赖

### 测试场景 2：启用 PAPI（系统包）

```bash
sudo apt-get install libpapi-dev
cd packages/sage-libs
ENABLE_PAPI=1 pip install -e .
```

预期：✅ 使用系统 PAPI，无需编译

### 测试场景 3：Benchmark 运行

```bash
cd packages/sage-benchmark/src/sage/benchmark/benchmark_amm
pip install -r requirements.txt
cd benchmark
./scripts/run_benchmark.py
```

预期：✅ Benchmark 正常运行（即使 PAPI 禁用）

## FAQ

### Q: 禁用 PAPI 会影响功能吗？

A: 不会。PAPI 仅用于硬件性能计数器采集，是可选的性能分析工具。核心 AMM 算法功能完全独立。

### Q: 什么时候需要 PAPI？

A: 仅在需要详细硬件性能分析时（CPU 指令数、缓存命中率等）。99% 的用户不需要。

### Q: 为什么不保留自行编译 PAPI？

A:

1. 编译失败率高（依赖内核头文件、硬件架构）
1. 增加构建时间（5-10 分钟）
1. 系统包更稳定、经过测试
1. 减少维护负担

### Q: 如何验证 PAPI 是否启用？

A: 检查编译日志：

- 禁用：`-- I will NOT use PAPI`
- 启用：`-- I will try to use PAPI for HW counters`

## 参考文档

- [PAPI 官方文档](http://icl.utk.edu/papi/)
- [Ubuntu libpapi-dev 包](https://packages.ubuntu.com/search?keywords=libpapi-dev)
- [CMake FindPkgConfig](https://cmake.org/cmake/help/latest/module/FindPkgConfig.html)
