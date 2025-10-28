# Tools Tests - 测试迁移说明

> ⚠️ **重要**: 本目录中的大部分测试文件已迁移到 `packages/sage-tools/tests/`

## 🎯 迁移状态

### ✅ 已迁移和清理的文件

以下文件已成功迁移到 `packages/sage-tools/tests/` 并从本目录删除：

- ✅ `conftest.py` → `packages/sage-tools/tests/conftest.py`
- ✅ `test_examples_imports.py` → `packages/sage-tools/tests/test_examples_imports.py`
- ✅ `example_strategies.py` → `packages/sage-tools/tests/examples/strategies.py`
- ✅ `pytest.ini` → 已删除（使用包级配置）
- ✅ `.pytest_cache/` → 已删除（缓存）
- ✅ `__pycache__/` → 已删除（缓存）
- ✅ `test_cpp_extensions.py` → 已删除（功能已集成到 sage-dev test）
- ✅ `test_embedding_optimization.py` → 已删除（功能已集成）
- ✅ `test_ci_commands.sh` → 已删除（已废弃）
- ✅ `test_ray_quick.sh` → 已删除（已废弃）

### ⚠️ 待处理的文件

以下文件仍在本目录，等待进一步评估和迁移：

#### 高优先级

1. **run_examples_tests.sh** - Examples 测试主脚本

   - 状态: 被 `.github/workflows/examples-test.yml` 使用
   - 计划: 更新 CI 使用 `sage-dev examples test` 后删除

1. **test_examples.py** - 完整的 Examples 测试套件 (31KB)

   - 状态: 部分功能已在 `sage-dev examples` 中实现
   - 计划: 评估功能完整性后决定是否迁移或删除

1. **test_examples_pytest.py** - pytest 集成

   - 状态: 与 test_examples.py 配合使用
   - 计划: 一起评估处理

#### 中优先级

4. **test_architecture_checker.py** - 架构检查器详细测试 (7.5KB)

   - 状态: `packages/sage-tools/tests/test_dev/test_quality_checkers.py` 只有基础测试
   - 计划: 对比并补充缺失的测试场景

1. **check_intermediate_results.py** - 中间结果检查工具

   - 状态: CLI 工具
   - 计划: 集成到 `sage-dev project check` 或迁移

## 📚 新位置

所有测试现在位于 `packages/sage-tools/tests/` 下：

```
packages/sage-tools/tests/
├── cli/                    # CLI 命令测试
├── dev/                    # 开发工具测试
│   └── test_quality_checkers.py  # 架构检查等
├── examples/               # Examples 测试
│   ├── demo_examples_testing.py
│   └── strategies.py       # 测试策略（新迁移）
├── pypi/                   # PyPI 安装测试
├── templates/              # 模板测试
└── test_examples_imports.py  # 示例导入测试
```

## 🚀 运行测试

### 使用 CLI 命令（推荐）

```bash
# 运行所有测试
sage-dev test

# 运行 Examples 测试
sage-dev examples test

# 运行快速测试
sage-dev examples test --quick

# 运行质量检查（包括架构检查）
sage-dev quality check
```

### 使用 pytest

```bash
# 进入 sage-tools 目录
cd packages/sage-tools

# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_examples_imports.py
pytest tests/examples/
pytest tests/dev/test_quality_checkers.py
```

## 📝 开发者注意事项

1. **不要在此目录添加新测试** - 所有新测试应添加到 `packages/sage-tools/tests/`
1. **使用 sage-dev 命令** - 优先使用 CLI 命令而不是直接运行脚本
1. **参考新结构** - 查看 `packages/sage-tools/tests/` 了解组织方式

## 🔗 相关文档

- 测试组织: `packages/sage-tools/tests/README.md`
- 清理总结: `docs/dev-notes/l6-tools/TOOLS_CLEANUP_SUMMARY.md`
- 开发指南: `DEVELOPER.md`

______________________________________________________________________

**最后更新**: 2025-10-28\
**状态**: 🚧 部分迁移完成，待进一步评估
