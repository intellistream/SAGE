# Pytest 配置策略

**Date**: 2025-10-29  
**Author**: SAGE Team  
**Summary**: SAGE 项目 pytest 配置策略说明，采用分布式配置+标准化模板的最佳实践

## 概述

SAGE 项目采用**分布式配置 + 标准化模板**的 pytest 配置策略（SOTA 最佳实践）。

## 设计原则

### ✅ 为什么不用集中式配置？

虽然集中式配置（单一 `pytest.ini`）在 monorepo 中更容易维护，但存在以下问题：

1. **不利于独立发布**：子包发布到 PyPI 后，无法携带测试配置
2. **不符合 Python 生态**：独立安装的包应该是自包含的
3. **工具兼容性差**：pytest 不支持像 ruff 那样的 `extend` 机制

### ✅ 我们的方案：分布式 + 模板化

每个子包的 `pyproject.toml` 包含完整的 pytest 配置，通过自动化工具保持一致性。

**优势**：
- ✅ 每个包可独立测试和发布
- ✅ 配置随包分发，不依赖 monorepo 结构
- ✅ 灵活性高，可按需定制（markers, filterwarnings）
- ✅ 符合 Python 包生态最佳实践

## 配置结构

### 标准配置（所有子包共享）

**注意**: 元包（`sage`）不包含实际代码，因此不需要 pytest 配置。

```toml
[tool.pytest.ini_options]
testpaths = ["tests", "src"]  # 统一的测试路径
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--benchmark-storage=../../.sage/benchmarks",
    "-o",
    "cache_dir=../../.sage/cache/pytest",
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "-ra",
]
```

### 目录结构要求

所有包（除元包外）必须遵循统一的目录结构：

```
package-name/
├── pyproject.toml
├── README.md
├── tests/          # 测试目录（必需）
│   └── __init__.py
└── src/            # 源代码目录（必需）
    └── sage/
        └── module_name/
```

**设计原则**:
- ✅ `testpaths` 统一为 `["tests", "src"]`
- ✅ 如果某个包的测试路径不同，说明代码结构需要调整
- ✅ 保持一致性优于灵活性

### 包特定配置

每个包可以自定义：

1. **markers**：测试标记（如 `@pytest.mark.slow`）
2. **filterwarnings**：警告过滤规则

示例：

```toml
# sage-kernel 特定配置
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "ray: marks tests requiring Ray framework",
]

filterwarnings = [
    "ignore::DeprecationWarning:ray._private.client_mode_hook",
]
```

## 使用方法

### 同步配置到所有子包

```bash
# 同步配置
python tools/sync_pytest_config.py

# 仅检查（不修改）
python tools/sync_pytest_config.py --check
```

### 添加新的包特定 marker

编辑 `tools/sync_pytest_config.py`：

```python
PACKAGE_MARKERS = {
    "sage": None,  # 元包不需要测试
    "sage-new-package": [
        "slow: marks tests as slow",
        "custom: marks tests as custom tests",
    ],
}
```

然后运行 `python tools/sync_pytest_config.py`。

**注意**: 元包（`sage`）设置为 `None`，表示跳过 pytest 配置。

### 添加 filterwarnings

编辑 `tools/sync_pytest_config.py`：

```python
PACKAGE_FILTERWARNINGS = {
    "sage-new-package": [
        "ignore::DeprecationWarning:some_module",
    ],
}
```

## CI/CD 集成

### Pre-commit Hook

在 `.pre-commit-config.yaml` 中添加：

```yaml
- repo: local
  hooks:
    - id: check-pytest-config
      name: Check pytest config consistency
      entry: python tools/sync_pytest_config.py --check
      language: system
      pass_filenames: false
```

### GitHub Actions

在 CI 工作流中添加检查步骤：

```yaml
- name: Check pytest config
  run: python tools/sync_pytest_config.py --check
```

## 常见问题

### Q: 为什么不直接在各子包手动维护配置？

A: 手动维护容易导致配置漂移（drift），难以确保一致性。自动化工具确保所有包使用相同的基础配置。

### Q: 如果需要修改标准配置怎么办？

A: 修改 `tools/sync_pytest_config.py` 中的 `STANDARD_PYTEST_CONFIG`，然后运行同步脚本。

### Q: 某个包需要完全不同的配置怎么办？

A: 可以在同步脚本中添加特殊逻辑，或者在该包的 `pyproject.toml` 中手动维护（需要在 CI 中排除检查）。

## 参考

- [Pytest Configuration](https://docs.pytest.org/en/stable/reference/customize.html)
- [Python Packaging Best Practices](https://packaging.python.org/en/latest/guides/)
- [Monorepo Testing Strategies](https://monorepo.tools/#testing)

---

**维护者**: SAGE Core Team  
**最后更新**: 2025-10-29
