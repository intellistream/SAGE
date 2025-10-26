# Quality Tools Configuration

此目录包含所有代码质量检查工具的配置文件。

## 配置文件

### Python 代码质量

- **`ruff.toml`** - Ruff linter 配置

  - 快速 Python linter 和代码格式化工具
  - 替代 flake8、isort、pyupgrade 等工具
  - **重要**: 排除了所有 git submodules 和第三方代码
    - `sageLLM` 是 git submodule (位于 `packages/sage-common/.../sageLLM`)
    - 使用完整路径排除以避免格式化 submodule 内部文件
  - 使用方式：`ruff check --config tools/quality/ruff.toml .`

- **`.flake8`** - Flake8 配置（已被 Ruff 替代）

  - 传统 Python linter
  - 保留用于兼容性
  - 同样排除 submodules 和 vendors 目录
  - 使用方式：`flake8 --config tools/quality/.flake8 .`

### 类型检查

- **`pyrightconfig.json`** - Pyright 类型检查配置
  - 静态类型检查器
  - VS Code Pylance 使用
  - 使用方式：`pyright --project tools/quality/pyrightconfig.json`

### 测试

- **`pytest.ini`** - Pytest 配置
  - Python 测试框架配置
  - 定义测试标记、路径等
  - 使用方式：`pytest -c tools/quality/pytest.ini`

## 使用方式

### 通过 sage dev quality 命令

推荐使用统一的质量检查命令：

```bash
# 运行所有检查并自动修复
sage dev quality

# 仅检查，不修复
sage dev quality --check-only

# 只运行特定检查
sage dev quality --ruff --no-format --no-type-check
```

### 直接使用工具

如果需要直接使用某个工具：

```bash
# Ruff
ruff check --config tools/quality/ruff.toml packages/

# Flake8
flake8 --config tools/quality/.flake8 packages/

# Pytest
pytest -c tools/quality/pytest.ini

# Pyright
pyright --project tools/quality/pyrightconfig.json
```

## 配置原则

1. **集中管理**：所有质量工具配置统一放在此目录
1. **一致性**：各工具配置保持一致的规则
1. **可扩展**：易于添加新工具或更新规则
1. **可复用**：可被 CI/CD、pre-commit、本地开发复用

## 相关文件

- `../pre-commit-config.yaml` - Pre-commit hooks 配置
- `../mypy-wrapper.sh` - Mypy 类型检查包装脚本
- `../secrets.baseline` - Secret detection baseline
