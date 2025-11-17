# LibAMM 安装指南

## 背景

LibAMM（Approximate Matrix Multiplication Library）是 SAGE 的**可选组件**，提供高性能的近似矩阵乘法算法。

由于 LibAMM 依赖 PyTorch C++ API，编译时内存占用极大：
- 单个源文件编译峰值：**500-700MB**
- 完整编译需要：**16GB+ 内存**
- WSL/虚拟机环境容易触发 OOM

因此，**LibAMM 默认不编译**，不影响 SAGE 其他功能的使用。

## 方案 1：使用预编译版本（推荐）

```bash
# 安装预编译的 LibAMM wheel 包（待发布）
pip install isage-libs-amm
```

预编译包的优势：
- ✅ 安装快速（秒级）
- ✅ 无内存压力
- ✅ 针对不同平台优化
- ✅ 包含 CUDA 和 CPU 版本

## 方案 2：从源码编译

### 前提条件

- **至少 16GB 可用内存**（物理内存 + swap）
- PyTorch >= 2.0.0
- GCC/G++ 11+

### 安装步骤

```bash
# 1. 安装 PyTorch（如果未安装）
pip install torch>=2.0.0

# 2. 设置环境变量并编译
BUILD_LIBAMM=1 pip install -e packages/sage-libs --no-build-isolation

# 或者在低内存环境（如 8GB WSL），先增加 swap
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 然后编译
BUILD_LIBAMM=1 pip install -e packages/sage-libs --no-build-isolation
```

### 内存优化

如果仍然遇到 OOM，LibAMM 的 CMakeLists.txt 已经包含了以下优化：

- **Unity Build**：每次只合并 2 个文件，减少头文件重复解析
- **优化级别降低**：`-O0` 而非 `-O3`，减少编译器内存占用
- **禁用调试符号**：`-g0`
- **单线程编译**：`CMAKE_BUILD_PARALLEL_LEVEL=1`
- **限制模板深度**：`-ftemplate-depth=128`
- **积极内存回收**：`--param ggc-min-expand=20`

即便如此，仍需要大内存环境才能顺利编译。

## 方案 3：在高性能机器上编译并分发

如果你是团队管理员：

```bash
# 在高内存服务器上
BUILD_LIBAMM=1 pip wheel packages/sage-libs --no-deps --no-build-isolation

# 生成的 wheel 文件可以分发给团队成员
pip install isage_libs-*.whl
```

## 验证安装

```python
# 检查 LibAMM 是否可用
try:
    from sage.libs.libamm.python import PyAMM
    print("✅ LibAMM 已安装并可用")
except ImportError as e:
    print(f"ℹ️  LibAMM 未安装（可选组件）: {e}")
```

## 常见问题

### Q: 没有 LibAMM，SAGE 能正常使用吗？
**A:** 可以。LibAMM 是可选组件，只有使用特定高性能矩阵算法时才需要。

### Q: 为什么默认不编译 LibAMM？
**A:** 因为 PyTorch C++ API 头文件展开后有 30 万行代码，编译器内存占用极大，不适合在普通开发环境下编译。

### Q: 如何判断我的环境是否适合编译 LibAMM？
**A:** 运行 `free -h` 检查：
- 可用内存 + swap >= 16GB：可以尝试
- 可用内存 + swap < 16GB：建议使用预编译版本

### Q: 编译时 OOM 怎么办？
**A:** 优先选择：
1. 使用预编译 wheel 包
2. 增加 swap 空间
3. 在云服务器/高内存机器上编译

## 技术细节

LibAMM 编译问题的根本原因：

```cpp
// PyTorch C++ API 的头文件
#include <torch/extension.h>  // 展开后 ~30 万行代码

// 编译器需要实例化大量模板
template<typename T> class Tensor { ... };  // 数千种模板实例化
```

每个源文件编译时，编译器需要：
1. 解析 30 万行头文件代码
2. 实例化数千个模板
3. 生成符号表和中间代码
4. 执行优化（`-O2` 或 `-O3`）

这导致 `cc1plus` 进程内存占用 500-700MB，在内存受限环境下触发 OOM killer。

## 贡献

如果你成功编译了 LibAMM，欢迎：
- 分享你的环境配置
- 提交预编译 wheel 包
- 报告编译问题
