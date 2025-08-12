# 解决 pytest-benchmark 错误的方法

## 问题描述

运行 `sage-dev test` 时遇到以下错误：
```
ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: unrecognized arguments: --benchmark-json /home/flecther/SAGE/.sage/reports/benchmark_report.json
```

## 问题原因

这个错误是因为 `pytest-benchmark` 插件没有安装，但 `sage-dev` 工具总是尝试添加 `--benchmark-json` 参数。

## 解决方案

### 方案1：自动安装脚本（推荐）

运行我们提供的安装脚本：

```bash
# 进入SAGE项目根目录
cd /home/flecther/SAGE

# 运行安装脚本
./scripts/install_test_deps.sh
```

这个脚本会：
- 安装所有必要的 pytest 插件
- 为所有 SAGE 包安装测试依赖
- 验证安装是否成功

### 方案2：手动安装

如果自动脚本有问题，可以手动安装：

```bash
# 安装基础 pytest 依赖
pip install \
    "pytest>=7.0.0" \
    "pytest-cov>=4.0.0" \
    "pytest-asyncio>=0.21.0" \
    "pytest-benchmark>=4.0.0" \
    "pytest-mock>=3.10.0"

# 为 sage-kernel 安装开发依赖
cd packages/sage-kernel
pip install -e ".[dev]"

# 为 sage-middleware 安装测试依赖
cd ../sage-middleware  
pip install -e ".[testing]"

# 为 sage-userspace 安装测试依赖
cd ../sage-userspace
pip install -e ".[testing]"

# 为 dev-toolkit 安装依赖
cd ../../dev-toolkit
pip install -e .

# 安装主项目
cd ..
pip install -e ".[dev]"
```

### 方案3：仅安装缺失的包

如果只想快速解决当前问题：

```bash
pip install pytest-benchmark>=4.0.0
```

## 验证安装

安装完成后，验证是否成功：

```bash
# 验证 pytest-benchmark 可用
python -c "import pytest_benchmark; print('pytest-benchmark is available')"

# 验证 sage-dev 可用
sage-dev --version

# 运行测试
sage-dev test
```

## 技术细节

### 问题根源

`sage-dev` 工具中的 `EnhancedTestRunner` 类总是添加 `--benchmark-json` 参数，但没有检查 `pytest-benchmark` 是否可用。

### 解决方案实现

我们修改了 `EnhancedTestRunner` 类：

1. 在初始化时检测 `pytest-benchmark` 是否可用
2. 只有在插件可用时才添加 benchmark 相关参数
3. 在所有相关包的 `pyproject.toml` 中添加了 `pytest-benchmark` 依赖

### 修改的文件

- `dev-toolkit/src/sage_dev_toolkit/tools/enhanced_test_runner.py`
- `packages/sage-kernel/pyproject.toml`
- `packages/sage-middleware/pyproject.toml` 
- `packages/sage-userspace/pyproject.toml`
- `dev-toolkit/pyproject.toml`

## 预防措施

为避免类似问题，建议：

1. 在开发环境中安装完整的开发依赖：
   ```bash
   pip install -e ".[dev]"  # 对于每个包
   ```

2. 使用提供的安装脚本来设置开发环境

3. 定期检查依赖是否完整：
   ```bash
   pip check
   ```

## 常见问题

### Q: 安装后仍然报错怎么办？

A: 尝试以下步骤：
1. 重启你的终端/shell
2. 检查 `which sage-dev` 确保使用正确版本
3. 重新安装 dev-toolkit：`pip install -e dev-toolkit/`

### Q: 在虚拟环境中如何安装？

A: 激活虚拟环境后运行相同的安装命令：
```bash
source your_venv/bin/activate  # 或 conda activate your_env
./scripts/install_test_deps.sh
```

### Q: 为什么需要 pytest-benchmark？

A: `pytest-benchmark` 用于性能基准测试，帮助我们：
- 监控代码性能回归
- 生成性能报告
- 比较不同版本的性能差异

虽然不是核心功能必需的，但对于确保代码质量很重要。
