# Python 维护脚本迁移完成 ✅

**日期**: 2025-10-27\
**任务**: 将 tools/maintenance/helpers/\*.py 迁移到 sage-tools 包

## ✅ 完成的工作

### 1. 创建新模块结构

```
packages/sage-tools/src/sage/tools/dev/maintenance/
├── __init__.py                 # 模块入口
├── devnotes_organizer.py       # Dev-notes 文档整理工具
├── metadata_fixer.py           # 元数据修复工具
└── ruff_updater.py             # Ruff 规则更新工具
```

### 2. 创建 CLI 命令

```
packages/sage-tools/src/sage/tools/cli/commands/dev/maintenance.py
```

新增命令:

- `sage-dev maintenance organize-devnotes` - 整理 dev-notes 文档
- `sage-dev maintenance fix-metadata` - 修复文档元数据
- `sage-dev maintenance update-ruff-ignore` - 更新 Ruff 规则
- `sage-dev maintenance list` - 列出所有维护工具

### 3. 更新原脚本添加迁移提示

所有原脚本 (`tools/maintenance/helpers/*.py`) 现在会：

1. 显示迁移警告
1. 提示新的使用方式
1. 尝试调用新模块（向后兼容）
1. 如果失败，保留原始代码运行

## 🚀 新的使用方式

### CLI 命令

```bash
# 列出所有维护工具
sage-dev maintenance list

# 整理 dev-notes 文档
sage-dev maintenance organize-devnotes
sage-dev maintenance organize-devnotes --quiet  # 简略输出

# 修复文档元数据
sage-dev maintenance fix-metadata
sage-dev maintenance fix-metadata --scan  # 扫描并修复所有文件

# 更新 Ruff ignore 规则
sage-dev maintenance update-ruff-ignore --preset b904-c901
sage-dev maintenance update-ruff-ignore --rules B904,C901,E501
```

### Python API

```python
from sage.tools.dev.maintenance import (
    DevNotesOrganizer,
    MetadataFixer,
    RuffIgnoreUpdater,
)

# 整理 dev-notes
organizer = DevNotesOrganizer(root_dir)
results = organizer.analyze_all()
report = organizer.generate_report(results)

# 修复元数据
fixer = MetadataFixer(root_dir)
stats = fixer.fix_all()

# 更新 Ruff 规则
updater = RuffIgnoreUpdater(root_dir)
stats = updater.add_b904_c901()
```

## 📊 迁移对比

| 方面     | 旧方式                                    | 新方式                                       | 改进                  |
| -------- | ----------------------------------------- | -------------------------------------------- | --------------------- |
| **位置** | `tools/maintenance/helpers/`              | `packages/sage-tools/`                       | ✅ 作为 Python 包分发 |
| **使用** | `python tools/maintenance/helpers/xxx.py` | `sage-dev maintenance xxx`                   | ✅ 统一 CLI 接口      |
| **导入** | 需要手动添加路径                          | `from sage.tools.dev.maintenance import ...` | ✅ 标准 Python 导入   |
| **帮助** | 在脚本内部                                | `--help` 选项                                | ✅ 标准化文档         |
| **输出** | 纯文本                                    | Rich UI（彩色、表格）                        | ✅ 更美观             |
| **测试** | 难以测试                                  | 可以单元测试                                 | ✅ 更可靠             |

## 🎯 功能对比

### 1. DevNotesOrganizer (原 devnotes_organizer.py)

**原功能**:

- 分析 dev-notes 文档
- 建议分类
- 检查元数据
- 生成整理报告

**新增**:

- ✅ Rich UI 输出
- ✅ 作为库使用
- ✅ 可编程接口
- ✅ 返回结构化数据

### 2. MetadataFixer (原 batch_fix_devnotes_metadata.py)

**原功能**:

- 批量修复元数据
- 预定义文件列表

**新增**:

- ✅ 扫描模式（`--scan`）
- ✅ 自动发现需要修复的文件
- ✅ 统计信息返回
- ✅ 更好的错误处理

### 3. RuffIgnoreUpdater (原 update_ruff_ignore.py)

**原功能**:

- 更新 pyproject.toml
- 添加 B904, C901

**新增**:

- ✅ 支持任意规则（`--rules`）
- ✅ 预设模式（`--preset`）
- ✅ 规则描述注释
- ✅ 统计信息

## 📁 文件状态

### 保留的文件（带迁移提示）

```
tools/maintenance/helpers/
├── devnotes_organizer.py      # ⚠️ 显示迁移警告，调用新模块
├── batch_fix_devnotes_metadata.py  # ⚠️ 显示迁移警告，调用新模块
└── update_ruff_ignore.py      # ⚠️ 显示迁移警告，调用新模块
```

### 新增的文件

```
packages/sage-tools/
├── src/sage/tools/dev/maintenance/
│   ├── __init__.py
│   ├── devnotes_organizer.py
│   ├── metadata_fixer.py
│   └── ruff_updater.py
└── src/sage/tools/cli/commands/dev/
    └── maintenance.py
```

## ✅ 测试验证

```bash
# 模块导入测试
python3 -c "from sage.tools.cli.commands.dev.maintenance import app"
# ✅ 通过

# CLI 命令测试
sage-dev maintenance list
# ✅ 显示 3 个维护工具

sage-dev maintenance organize-devnotes --quiet
# ✅ 成功分析 81 个文件
```

## 🎓 优势总结

### 1. 统一的用户体验

- 所有命令通过 `sage-dev` 访问
- 一致的选项格式（`--help`, `--verbose`, etc.）
- 统一的输出格式（Rich UI）

### 2. 更好的可维护性

- Python 包结构
- 清晰的模块划分
- 易于测试
- 类型提示

### 3. 更强的功能性

- 可编程 API
- 返回结构化数据
- 更好的错误处理
- 可扩展设计

### 4. 向后兼容

- 原脚本仍可使用
- 显示迁移提示
- 自动调用新模块

## 📝 后续建议

### 短期

1. ✅ 更新文档引用新命令
1. ✅ 在 CI/CD 中使用新命令
1. ✅ 添加单元测试

### 中期

4. 考虑添加更多维护工具
1. 完善错误处理
1. 添加进度条（长时间操作）

### 长期

7. 一段时间后（如 3-6 个月）删除旧脚本
1. 完全迁移到新的 CLI 体系

## 🔄 与整体迁移策略一致

这次迁移遵循了 `TOOLS_MIGRATION_ANALYSIS.md` 中的建议：

- ✅ Python 脚本 → 迁移到 sage-tools
- ✅ 集成到 sage-dev CLI
- ✅ 保留向后兼容
- ✅ 添加废弃提示
- ✅ 双轨制过渡

下一步可以考虑：

- 迁移更多 Python 脚本
- 集成 `tools/dev.sh` 功能到 sage-dev
- 增强其他命令组

______________________________________________________________________

**状态**: ✅ 完成\
**测试**: ✅ 通过\
**文档**: ✅ 完善
