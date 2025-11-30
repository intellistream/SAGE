# 缓存管理配置说明

**Date**: 2025-10-29  
**Author**: GitHub Copilot  
**Summary**: 统一管理开发工具缓存到 .sage/cache/ 目录，包括 Mypy、Ruff、Pytest 等工具的缓存配置和清理方法

## 概述

为了更好地管理项目的中间产物和缓存文件，我们将所有开发工具的缓存统一规划到 `.sage/cache/` 目录下。

## 缓存目录结构

```
.sage/
├── cache/
│   ├── mypy/          # Mypy 类型检查缓存
│   ├── ruff/          # Ruff 代码检查缓存
│   └── pytest/        # Pytest 测试缓存
├── checkpoints/       # 容错机制 checkpoint 存储
├── test_checkpoints/  # 测试用 checkpoint 存储
├── benchmarks/        # 基准测试结果
├── logs/              # 日志文件
├── reports/           # 测试报告
└── ...
```

## 配置方式

### 1. Mypy 缓存

Mypy 缓存通过各个包的 `pyproject.toml` 配置：

```toml
[tool.mypy]
cache_dir = "../../.sage/cache/mypy"
```

所有子包都已配置指向统一的缓存目录。

### 2. Ruff 缓存

Ruff 缓存通过环境变量 `RUFF_CACHE_DIR` 配置。在项目根目录的 `.env` 文件中添加：

```bash
RUFF_CACHE_DIR=.sage/cache/ruff
```

或在运行命令时指定：

```bash
export RUFF_CACHE_DIR=.sage/cache/ruff
ruff check .
```

### 3. Pytest 缓存

Pytest 缓存已在各个包的 `pyproject.toml` 中配置：

```toml
[tool.pytest.ini_options]
addopts = [
    "-o",
    "cache_dir=../../.sage/cache/pytest",
    # ... 其他选项
]
```

## 清理缓存

### 使用清理脚本

```bash
# 清理所有缓存和构建产物
./manage.sh clean

# 深度清理（包括 Python 缓存、日志等）
./manage.sh clean-deep
```

### 手动清理

如果需要手动清理特定缓存：

```bash
# 清理 mypy 缓存
rm -rf .sage/cache/mypy

# 清理 ruff 缓存
rm -rf .sage/cache/ruff

# 清理 pytest 缓存
rm -rf .sage/cache/pytest
```

## 环境变量配置

在 `.env` 文件中（从 `.env.template` 复制）添加：

```bash
# Ruff cache directory (for linting)
RUFF_CACHE_DIR=.sage/cache/ruff

# Mypy cache directory (for type checking)
MYPY_CACHE_DIR=.sage/cache/mypy
```

> **注意**: Mypy 的 `MYPY_CACHE_DIR` 环境变量是可选的，因为我们已经在 `pyproject.toml` 中配置了 `cache_dir`。

## 优势

1. **集中管理**: 所有缓存文件都在 `.sage/cache/` 目录下，便于统一管理和清理
2. **避免污染**: 不会在各个子包目录下产生 `.mypy_cache`、`.ruff_cache` 等散落的缓存目录
3. **简化清理**: 一个命令即可清理所有缓存
4. **版本控制**: `.sage/` 目录已在 `.gitignore` 中，不会被提交到版本控制

## 相关文件

- `.env.template`: 环境变量配置模板
- `tools/maintenance/helpers/quick_cleanup.sh`: 清理脚本
- `tools/ruff.toml`: Ruff 统一配置
- `packages/*/pyproject.toml`: 各包的配置文件

## 更新历史

- 2025-01-XX: 初始配置，将所有缓存统一到 `.sage/cache/` 目录
