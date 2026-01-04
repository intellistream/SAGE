# 子模块开发指南

## 概述

SAGE 项目中的子模块（sageLLM, sageVDB, sageFlow, neuromem, sageTSDB, sageRefiner）都是独立的 Git
仓库，有自己的开发工具链和测试框架。

## 子模块列表

| 子模块          | 类型   | 路径                                                                               | 描述              |
| --------------- | ------ | ---------------------------------------------------------------------------------- | ----------------- |
| **sageLLM**     | Python | `packages/sage-llm-core/src/sage/llm/sageLLM`                                      | LLM Control Plane |
| **sageVDB**     | C++    | `packages/sage-middleware/src/sage/middleware/components/sage_db/sageVDB`          | 向量数据库        |
| **sageFlow**    | C++    | `packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow`       | 流处理引擎        |
| **neuromem**    | Python | `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem`        | 记忆系统          |
| **sageTSDB**    | C++    | `packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB`       | 时序数据库        |
| **sageRefiner** | Python | `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner` | 上下文压缩        |

## 开发工具配置

每个子模块都有独立的开发工具配置：

### Pre-commit Hooks

**C++ 子模块** (sageVDB, sageFlow, sageTSDB):

- `clang-format` - C++ 代码格式化
- `cmake-format` - CMake 格式化
- `cmake-lint` - CMake 检查
- `ruff` - Python 绑定代码格式化
- 通用检查（trailing-whitespace, end-of-file, yaml/json/toml）

**Python 子模块** (sageLLM, neuromem, sageRefiner):

- `ruff` - Python 代码格式化和 lint
- `mypy` - 类型检查
- 通用检查（trailing-whitespace, end-of-file, yaml/json/toml）

**所有子模块**:

- `shellcheck` - Shell 脚本检查
- `mdformat` - Markdown 格式化
- `detect-secrets` - 敏感信息检测

### Pytest 配置

所有子模块都有 `pytest.ini` 配置：

- 测试发现模式
- 异步测试支持
- 日志配置
- 测试标记（unit, integration, slow, gpu, cpp）
- 覆盖率报告

## 开发工作流

### 1. 初始化子模块

```bash
# 克隆主项目后，初始化子模块
./manage.sh

# 或手动初始化
git submodule update --init --recursive
```

### 2. 在子模块中开发

```bash
# 进入子模块目录
cd packages/sage-middleware/src/sage/middleware/components/sage_db/sageVDB

# 安装 pre-commit hooks
pre-commit install

# 运行所有检查
pre-commit run --all-files

# 修改代码...

# 运行测试
pytest

# 提交更改（会自动运行 pre-commit hooks）
git add .
git commit -m "feat: add new feature"

# 推送到子模块远端
git push
```

### 3. 更新主项目的子模块引用

```bash
# 回到主项目根目录
cd /path/to/SAGE

# 更新子模块引用
git add packages/sage-middleware/src/sage/middleware/components/sage_db/sageVDB

# 提交主项目
git commit -m "chore: update sageVDB submodule"
```

## 常见任务

### 运行测试

```bash
# 在子模块目录中
cd packages/sage-llm-core/src/sage/llm/sageLLM

# 运行所有测试
pytest

# 运行特定标记的测试
pytest -m unit              # 只运行单元测试
pytest -m "not slow"        # 跳过慢速测试
pytest -m gpu               # 只运行 GPU 测试

# 运行特定文件
pytest tests/test_manager.py

# 带覆盖率
pytest --cov=. --cov-report=html
```

### 代码格式化

```bash
# C++ 子模块
clang-format -i src/*.cpp include/*.h

# Python 子模块
ruff format .

# 或使用 pre-commit
pre-commit run --all-files
```

### 类型检查

```bash
# Python 子模块
mypy .

# 或通过 pre-commit
pre-commit run mypy --all-files
```

## 添加新的测试

### 测试文件结构

```
submodule/
├── tests/
│   ├── __init__.py
│   ├── unit/                  # 单元测试
│   │   ├── test_core.py
│   │   └── test_utils.py
│   ├── integration/           # 集成测试
│   │   └── test_pipeline.py
│   └── fixtures/              # 测试数据和 fixtures
│       └── conftest.py
├── pytest.ini
└── .pre-commit-config.yaml
```

### 测试示例

```python
# tests/unit/test_example.py
import pytest

@pytest.mark.unit
def test_basic_function():
    """Basic unit test"""
    assert True

@pytest.mark.integration
@pytest.mark.slow
def test_slow_integration():
    """Slow integration test"""
    # ...

@pytest.mark.gpu
def test_gpu_feature():
    """Test requiring GPU"""
    # ...

@pytest.mark.cpp
def test_cpp_binding():
    """Test for C++ Python bindings"""
    # ...
```

## 添加新的 Pre-commit Hook

编辑子模块的 `.pre-commit-config.yaml`:

```yaml
repos:
  # 添加新的 hook
- repo: https://github.com/example/hook
  rev: v1.0.0
  hooks:
  - id: my-hook
    args: [--option]
```

然后运行：

```bash
pre-commit install
pre-commit run my-hook --all-files
```

## CI/CD 集成

### 子模块 CI

每个子模块应该有自己的 CI 配置（`.github/workflows/ci.yml`）：

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install pre-commit pytest pytest-cov

    - name: Run pre-commit
      run: pre-commit run --all-files

    - name: Run tests
      run: pytest --cov
```

### 主项目 CI

主项目的 CI 会运行所有子模块的测试：

```bash
# 在 .github/workflows/build-test.yml 中
./quickstart.sh --dev --yes
sage-dev project test --coverage
```

## 故障排除

### Pre-commit Hook 失败

```bash
# 跳过 hooks 提交（紧急情况）
git commit --no-verify

# 只运行特定 hook
pre-commit run ruff --all-files

# 更新 hooks 到最新版本
pre-commit autoupdate
```

### 测试失败

```bash
# 详细输出
pytest -vv

# 停在第一个失败
pytest -x

# 显示本地变量
pytest -l

# 进入调试器
pytest --pdb
```

### 子模块同步问题

```bash
# 确保子模块在正确的分支
cd submodule
git checkout main
git pull

# 回到主项目更新引用
cd /path/to/SAGE
git add submodule
git commit -m "chore: update submodule"
```

## 最佳实践

1. **独立开发**: 每个子模块应该能够独立开发、测试和发布
1. **文档同步**: 子模块的文档应该与代码在一起
1. **版本管理**: 使用语义化版本（semver）
1. **测试覆盖**: 保持高测试覆盖率（>80%）
1. **代码质量**: 所有提交前必须通过 pre-commit hooks
1. **向后兼容**: API 变更要考虑向后兼容性
1. **变更日志**: 维护 CHANGELOG.md 记录重要变更

## 相关文档

- [主项目开发指南](../../DEVELOPER.md)
- [文档位置策略](../../.github/copilot-instructions.md#documentation-location-policy---critical)
- [Pre-commit 官方文档](https://pre-commit.com/)
- [Pytest 官方文档](https://docs.pytest.org/)

## 自动化脚本

### 批量更新子模块

```bash
# 更新所有子模块到最新版本
./tools/maintenance/sage-maintenance.sh submodule update

# 切换所有子模块到主分支
./tools/maintenance/sage-maintenance.sh submodule switch
```

### 批量安装 Pre-commit Hooks

```bash
# 为所有子模块安装 hooks
for submodule in packages/*/src/*/*/; do
    if [ -f "$submodule/.pre-commit-config.yaml" ]; then
        (cd "$submodule" && pre-commit install)
    fi
done
```

### 批量运行测试

```bash
# 运行所有子模块的测试
for submodule in packages/*/src/*/*/; do
    if [ -f "$submodule/pytest.ini" ]; then
        echo "Testing $(basename $submodule)..."
        (cd "$submodule" && pytest)
    fi
done
```
