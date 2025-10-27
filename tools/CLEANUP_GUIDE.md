# 清理已迁移文件指南

## 📋 概述

以下文件已成功迁移到 `packages/sage-tools`，可以安全删除：

### ✅ 已迁移的文件

| 原文件 | 新位置 | CLI 命令 | 状态 |
|--------|--------|---------|------|
| `tools/maintenance/helpers/devnotes_organizer.py` | `sage.tools.dev.maintenance.devnotes_organizer` | `sage-dev maintenance organize-devnotes` | ✅ 已测试 |
| `tools/maintenance/helpers/batch_fix_devnotes_metadata.py` | `sage.tools.dev.maintenance.metadata_fixer` | `sage-dev maintenance fix-metadata` | ✅ 已测试 |
| `tools/maintenance/helpers/update_ruff_ignore.py` | `sage.tools.dev.maintenance.ruff_updater` | `sage-dev maintenance update-ruff-ignore` | ✅ 已测试 |
| `tools/tests/check_intermediate_results.py` | `sage.tools.dev.examples.suite` | `sage-dev examples check` | ✅ 已测试 |
| `tools/tests/example_strategies.py` | `sage.tools.dev.examples.strategies` | 集成到模块 | ✅ 已测试 |
| `tools/tests/test_examples.py` | `sage.tools.dev.examples.runner` | `sage-dev examples test` | ✅ 已测试 |
| `tools/tests/test_examples_pytest.py` | 集成到 sage-tools | 集成到模块 | ✅ 已测试 |
| `tools/tests/pytest.ini` | `packages/sage-tools/tests/` | - | ✅ 已迁移 |
| `tools/tests/conftest.py` | `packages/sage-tools/tests/` | - | ✅ 已迁移 |

## 🔧 清理方法

### 方法 1: 安全清理（推荐）

使用 `SAFE_CLEANUP.sh` 会先备份再删除：

```bash
cd /home/shuhao/SAGE/tools
./SAFE_CLEANUP.sh
```

**优点：**
- ✅ 自动备份到 `tools/backup_YYYYMMDD_HHMMSS/`
- ✅ 可以轻松恢复
- ✅ 有详细的操作记录

**备份位置：**
- `tools/backup_YYYYMMDD_HHMMSS/` - 包含所有删除的文件

**恢复方法：**
```bash
# 如果需要恢复
cp -r tools/backup_YYYYMMDD_HHMMSS/* tools/
```

### 方法 2: 直接删除

使用 `CLEANUP_MIGRATED_FILES.sh` 直接删除（不备份）：

```bash
cd /home/shuhao/SAGE/tools
./CLEANUP_MIGRATED_FILES.sh
```

**注意：**
- ⚠️ 不会创建备份
- ⚠️ 需要从 Git 历史恢复

### 方法 3: 手动删除

如果你想自己控制删除过程：

```bash
# 删除维护脚本
rm tools/maintenance/helpers/devnotes_organizer.py
rm tools/maintenance/helpers/batch_fix_devnotes_metadata.py
rm tools/maintenance/helpers/update_ruff_ignore.py

# 删除测试文件
rm tools/tests/check_intermediate_results.py
rm tools/tests/example_strategies.py
rm tools/tests/run_examples_tests.sh
rm tools/tests/test_examples.py
rm tools/tests/test_examples_pytest.py
rm tools/tests/pytest.ini
rm tools/tests/conftest.py

# 删除 __pycache__
rm -rf tools/tests/__pycache__
rm -rf tools/maintenance/helpers/__pycache__
```

## ✅ 验证清理

清理后，验证新命令是否正常工作：

```bash
# 测试维护命令
sage-dev maintenance organize-devnotes
sage-dev maintenance fix-metadata --help
sage-dev maintenance update-ruff-ignore --help

# 测试 examples 命令
sage-dev examples analyze
sage-dev examples info
sage-dev examples --help

# 测试文档命令
sage-dev docs check
sage-dev docs --help
```

## 📊 清理前后对比

### 清理前
```
tools/
├── maintenance/
│   └── helpers/
│       ├── devnotes_organizer.py          ❌ 旧文件
│       ├── batch_fix_devnotes_metadata.py ❌ 旧文件
│       └── update_ruff_ignore.py          ❌ 旧文件
└── tests/
    ├── check_intermediate_results.py      ❌ 旧文件
    ├── example_strategies.py              ❌ 旧文件
    ├── test_examples.py                   ❌ 旧文件
    └── ...
```

### 清理后
```
tools/
├── maintenance/
│   └── helpers/
│       ├── check_config_security.sh       ✅ 保留
│       └── ...（其他 Shell 脚本）
└── tests/
    ├── test_architecture_checker.py       ✅ 保留
    ├── test_ci_commands.sh                ✅ 保留
    └── ...（未迁移的测试）
```

## 🎯 迁移后的新用法

### 维护工具

```bash
# 旧: python tools/maintenance/helpers/devnotes_organizer.py
# 新:
sage-dev maintenance organize-devnotes

# 旧: python tools/maintenance/helpers/batch_fix_devnotes_metadata.py
# 新:
sage-dev maintenance fix-metadata

# 旧: python tools/maintenance/helpers/update_ruff_ignore.py B904,C901
# 新:
sage-dev maintenance update-ruff-ignore --rules B904,C901
```

### Examples 测试

```bash
# 旧: python tools/tests/test_examples.py
# 新:
sage-dev examples test

# 旧: python tools/tests/check_intermediate_results.py
# 新:
sage-dev examples check

# 新增功能:
sage-dev examples analyze
sage-dev examples info
```

## 📝 注意事项

### ⚠️ 暂时保留的文件

以下文件暂时保留，因为：

1. **`tools/dev.sh`** - 还有其他功能未迁移
2. **`tools/tests/test_architecture_checker.py`** - 独立的测试，未迁移
3. **`tools/tests/test_ci_commands.sh`** - Shell 测试，未迁移
4. **`tools/maintenance/helpers/` 下的 Shell 脚本** - 未迁移

### ✅ 已添加废弃警告

所有迁移的 Python 脚本都已添加废弃警告：
- 运行时会显示迁移提示
- 提供新的使用方式
- 仍可正常工作（向后兼容）

## 🔄 恢复选项

如果删除后需要恢复：

### 从备份恢复（如果使用 SAFE_CLEANUP.sh）
```bash
cp -r tools/backup_YYYYMMDD_HHMMSS/* tools/
```

### 从 Git 恢复
```bash
# 恢复单个文件
git checkout HEAD -- tools/maintenance/helpers/devnotes_organizer.py

# 恢复整个目录
git checkout HEAD -- tools/maintenance/helpers/
git checkout HEAD -- tools/tests/
```

## 📈 迁移进度

- ✅ **Phase 1**: 核心功能迁移（已完成）
  - ✅ Examples 测试框架
  - ✅ 维护工具（3个）
  - ✅ 文档管理命令

- ✅ **Phase 2**: 测试覆盖（已完成）
  - ✅ 单元测试 (39个)
  - ✅ 集成测试
  - ✅ CLI 测试

- 🔄 **Phase 3**: 清理旧文件（当前阶段）
  - 🔄 删除已迁移的文件
  - ⏳ 评估其他文件

- ⏳ **Phase 4**: 完全迁移（未来）
  - ⏳ 迁移 `tools/dev.sh` 其余功能
  - ⏳ 迁移其他 Shell 脚本

## 💡 建议

1. **先使用 SAFE_CLEANUP.sh**（有备份）
2. **测试新命令** 确保一切正常
3. **确认无误后** 删除备份
4. **更新 CI/CD** 使用新命令

## 🎉 总结

清理这些文件是安全的，因为：

- ✅ 所有功能已完整迁移
- ✅ 所有功能已充分测试（39个测试全部通过）
- ✅ 新 CLI 提供更好的体验
- ✅ 有多种恢复方式
- ✅ 旧文件已添加废弃警告

---

**推荐操作顺序：**

1. 运行 `./SAFE_CLEANUP.sh` 清理并备份
2. 测试新命令是否正常工作
3. 确认无误后删除备份目录
4. 提交 Git 更改

**文档：** 详见 `TOOLS_MIGRATION_PROGRESS.md`
