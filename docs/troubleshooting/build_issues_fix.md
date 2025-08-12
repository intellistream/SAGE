# 构建问题修复指南

## 问题描述

在运行构建脚本时遇到以下问题：

1. **outlines_core 构建失败**：
   ```
   ERROR: Failed building wheel for outlines_core
   ```

2. **xformers 弃用警告**：
   ```
   DEPRECATION: Building 'xformers' using the legacy setup.py bdist_wheel mechanism
   ```

## 问题原因

### outlines_core 问题
- `outlines_core` 是 `outlines` 包的 Rust 编写的核心组件
- 需要 Rust 编译器环境
- 某些平台没有预编译的二进制包

### xformers 问题  
- `xformers` 使用了即将被弃用的 `setup.py` 构建机制
- 新版本的 pip (25.3+) 将强制使用 PEP 517 标准

## 解决方案

### 🚀 快速解决（推荐）

使用我们提供的快速修复脚本：

```bash
# 运行快速修复
./scripts/quick_fix_build.sh
```

### 🔧 完整解决方案

如果需要完整的环境修复：

```bash
# 运行完整修复
./scripts/fix_build_issues.sh

# 使用修复版本构建
./scripts/build_with_fixes.sh
```

### 📦 使用预构建包（最快）

如果只需要安装 SAGE，直接使用锁定依赖：

```bash
pip install -r requirements-lock.txt
```

## 技术细节

### 修复的内容

1. **Rust 环境设置**：
   - 自动安装 Rust 编译器（如果缺失）
   - 配置 Rust 构建环境变量

2. **构建工具升级**：
   - 升级 pip、setuptools、wheel 到最新版本
   - 安装 `setuptools-rust` 和 `maturin`

3. **PEP 517 支持**：
   - 为 xformers 启用 `--use-pep517` 选项
   - 设置 `PIP_USE_PEP517=1` 环境变量

4. **依赖约束**：
   - 创建 `constraints-build.txt` 约束文件
   - 固定兼容的版本组合

### 环境变量设置

脚本会设置以下环境变量：

```bash
export PIP_USE_PEP517=1           # 启用 PEP 517
export PIP_PREFER_BINARY=1        # 优先二进制包
export PIP_ONLY_BINARY=":all:"    # 强制二进制包
export RUSTFLAGS="-C target-cpu=native"  # Rust 优化
```

## 验证修复

修复完成后，可以验证安装：

```bash
# 验证 outlines 安装
python -c "import outlines; print('outlines:', outlines.__version__)"

# 验证 xformers 安装  
python -c "import xformers; print('xformers:', xformers.__version__)"

# 验证 PyTorch 兼容性
python -c "import torch, xformers; print('PyTorch:', torch.__version__, 'CUDA:', torch.cuda.is_available())"
```

## 预防措施

为避免将来的构建问题：

1. **使用锁定依赖**：优先使用 `requirements-lock.txt`
2. **环境准备**：提前安装 Rust 和构建工具
3. **约束文件**：使用 `constraints-build.txt` 避免冲突
4. **CI/CD 优化**：在构建流程中包含这些修复

## 故障排除

如果修复脚本失败：

1. **检查网络连接**：确保可以下载 Rust 安装器
2. **权限问题**：确保有写入 `~/.cargo` 的权限
3. **磁盘空间**：确保有足够空间安装 Rust（~1GB）
4. **手动安装 Rust**：
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source ~/.cargo/env
   ```

## 相关链接

- [outlines GitHub](https://github.com/outlines-dev/outlines)
- [xformers GitHub](https://github.com/facebookresearch/xformers)
- [PEP 517 标准](https://peps.python.org/pep-0517/)
- [Rust 安装指南](https://rustup.rs/)
