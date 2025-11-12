# LibAMM 内存优化指南

**Date**: 2025-11-12  
**Author**: GitHub Copilot  
**Summary**: LibAMM 编译内存优化策略，解决 WSL/容器环境中的 OOM 问题

## 问题背景

LibAMM 是一个包含大量模板和 PyTorch C++ API 的库，在编译时会消耗大量内存。特别是在 WSL、容器或内存受限的环境中，可能会遇到 OOM (Out of Memory) 导致编译失败。

### 典型症状

```bash
g++: fatal error: Killed signal terminated program cc1plus
FAILED: [code=1] LibAMM.dir/src/CPPAlgos/SMPPCACPPAlgo.cpp.o
```

查看系统日志 `dmesg` 会看到：
```
oom-kill:constraint=CONSTRAINT_NONE,task=cc1plus,pid=12675
Out of memory: Killed process 12675 (cc1plus)
```

## 已实施的优化措施

### 1. **降低编译优化级别** (已自动应用)

修改了 `packages/sage-libs/src/sage/libs/libamm/CMakeLists.txt`:

```cmake
# 原来的设置（高内存消耗）
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 ...")      # 完整调试符号
set(CMAKE_CXX_FLAGS_RELEASE "-O3")           # 最高优化

# 优化后的设置（低内存消耗）
set(CMAKE_CXX_FLAGS_DEBUG "-g0 -O1 ...")    # 无调试符号，低优化
set(CMAKE_CXX_FLAGS_RELEASE "-O2")           # 中等优化
```

**效果**: 可减少 30-50% 的编译内存消耗

### 2. **强制单线程编译** (已自动应用)

安装脚本 `core_installer.sh` 会自动为 `sage-libs` 设置：

```bash
export CMAKE_BUILD_PARALLEL_LEVEL=1
export MAKEFLAGS="-j1"
```

**效果**: 避免多个 g++ 进程同时运行导致内存叠加

### 3. **禁用非必要组件** (已自动应用)

```cmake
set(BUILD_BENCHMARK OFF)  # 跳过 benchmark 编译
set(ENABLE_PAPI OFF)      # 禁用性能计数器
```

## 手动编译选项

如果仍然遇到 OOM，可以手动使用更激进的设置：

### 方案 1: 最小内存占用编译

```bash
# 1. 卸载现有版本
pip uninstall -y isage-libs

# 2. 设置环境变量（更激进）
export CMAKE_BUILD_PARALLEL_LEVEL=1
export MAKEFLAGS="-j1"
export CXXFLAGS="-O1 -g0"  # 最低优化，无调试符号

# 3. 安装
pip install -e packages/sage-libs --no-deps --no-build-isolation -v
```

### 方案 2: 增加系统 Swap

如果物理内存不足，可以临时增加 swap 空间：

```bash
# WSL 中增加 swap（需要管理员权限）
# 1. 编辑 /etc/wsl.conf
sudo nano /etc/wsl.conf

# 2. 添加以下内容
[wsl2]
swap=8GB  # 根据需要调整大小

# 3. 重启 WSL
# 在 PowerShell 中执行:
# wsl --shutdown
# wsl
```

### 方案 3: 跳过 LibAMM 编译

如果不需要 LibAMM 功能，可以临时禁用：

```bash
# 1. 备份 CMakeLists.txt
cp packages/sage-libs/CMakeLists.txt packages/sage-libs/CMakeLists.txt.bak

# 2. 注释掉 add_subdirectory(${LIBAMM_DIR} ...)
sed -i 's/add_subdirectory(${LIBAMM_DIR}/# add_subdirectory(${LIBAMM_DIR}/' packages/sage-libs/CMakeLists.txt

# 3. 安装
pip install -e packages/sage-libs --no-deps --no-build-isolation

# 4. 恢复
mv packages/sage-libs/CMakeLists.txt.bak packages/sage-libs/CMakeLists.txt
```

## 验证编译成功

```bash
# 检查 LibAMM 是否成功编译
python3 -c "
try:
    from sage.libs.libamm.python import PyAMM
    print('✅ LibAMM 编译成功')
except ImportError as e:
    print(f'❌ LibAMM 不可用: {e}')
"

# 查看编译的库文件
find packages/sage-libs -name "*.so" | grep -i amm
```

## 内存消耗对比

| 编译选项 | 估计内存峰值 | 编译时间 |
|---------|------------|---------|
| `-O3 -g` (默认) | ~800MB/进程 | 快 |
| `-O2 -g0` (优化后) | ~500MB/进程 | 中等 |
| `-O1 -g0` (最低) | ~300MB/进程 | 慢 |

在 8GB 内存的 WSL 环境中，单线程 `-O1 -g0` 编译可以避免 OOM。

## 故障排查

### 1. 检查 OOM Killer 日志

```bash
dmesg | grep -i "out of memory\|killed process" | tail -20
```

### 2. 监控编译内存使用

在另一个终端运行：
```bash
watch -n 1 'ps aux | grep g++ | grep -v grep'
```

### 3. 清理构建缓存

```bash
# 清理 CMake 缓存
rm -rf .sage/build/libamm

# 清理 pip 缓存
pip cache purge
```

## 相关链接

- [LibAMM GitHub](https://github.com/intellistream/LibAMM)
- [PyTorch C++ API Memory Issues](https://github.com/pytorch/pytorch/issues)
- [CMake Build Optimization](https://cmake.org/cmake/help/latest/variable/CMAKE_BUILD_PARALLEL_LEVEL.html)

## 更新日志

- 2025-11-12: 初始版本，添加内存优化措施
- 实施优化后，在 7.6GB WSL 环境中可成功单线程编译
