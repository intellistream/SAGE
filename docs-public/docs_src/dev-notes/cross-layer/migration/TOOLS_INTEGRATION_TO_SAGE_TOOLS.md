**Date**: 2025-10-26\
**Author**: sage-development Team\
**Summary**: 将 tools/ 目录下的质量检查工具集成到 sage-tools 包中，提供统一的 CLI 接口

______________________________________________________________________

# Tools 集成到 sage-tools 包

## 📋 概述

将 `tools/` 根目录下的开发质量检查工具集成到 `sage-tools` 包中，并提供统一的 CLI 命令接口。

## 🎯 目标

1. **统一管理**: 将所有 Python 开发工具集成到 `sage-tools` 包中
1. **CLI 接口**: 通过 `sage-dev` 命令提供一致的用户体验
1. **可维护性**: 工具作为 Python 包管理，有测试、版本控制
1. **可重用性**: 其他模块可以导入使用这些检查器

## 📦 迁移的工具

### 1. architecture_checker.py → sage-dev check-architecture

**原路径**: `tools/architecture_checker.py`\
**新路径**: `packages/sage-tools/src/sage/tools/dev/tools/architecture_checker.py`

**功能**: 检查 SAGE 分层架构合规性

- 包依赖规则检查
- 导入路径合规性
- 模块结构规范

**新命令**:

```bash
# 检查所有文件
sage-dev check-architecture

# 仅检查变更文件
sage-dev check-architecture --changed-only

# 对比特定分支
sage-dev check-architecture --diff main
```

**集成到 quality 命令**:

```bash
# 默认包含架构检查
sage-dev quality

# 跳过架构检查
sage-dev quality --no-architecture
```

### 2. devnotes_checker.py → sage-dev check-devnotes

**原路径**: `tools/devnotes_checker.py`\
**新路径**: `packages/sage-tools/src/sage/tools/dev/tools/devnotes_checker.py`

**功能**: 检查 dev-notes 文档规范

- 文档分类是否正确
- 元数据完整性（Date, Author, Summary）
- 文件名规范

**新命令**:

```bash
# 检查所有文档
sage-dev check-devnotes

# 仅检查变更的文档
sage-dev check-devnotes --changed-only

# 检查目录结构
sage-dev check-devnotes --check-structure
```

**集成到 quality 命令**:

```bash
# 默认包含文档检查
sage-dev quality

# 跳过文档检查
sage-dev quality --no-devnotes
```

### 3. package_readme_checker.py → sage-dev check-readme

**原路径**: `tools/package_readme_checker.py`\
**新路径**: `packages/sage-tools/src/sage/tools/dev/tools/package_readme_checker.py`

**功能**: 检查各包 README 文档质量

- README 文件存在性
- 必需章节完整性
- 文档结构规范

**新命令**:

```bash
# 检查所有包
sage-dev check-readme

# 检查特定包
sage-dev check-readme sage-common

# 生成详细报告
sage-dev check-readme --report

# 交互式修复
sage-dev check-readme sage-libs --fix
```

**集成到 quality 命令**:

```bash
# 包含 README 检查（默认不包含）
sage-dev quality --readme
```

## 🗂️ 移动到 maintenance 的工具

以下工具移动到 `tools/maintenance/helpers/`，作为一次性使用或辅助工具：

### 1. devnotes_organizer.py

**路径**: `tools/maintenance/helpers/devnotes_organizer.py`

**用途**: 辅助整理现有 dev-notes 文档，建议分类目录

**使用方式**:

```bash
python tools/maintenance/helpers/devnotes_organizer.py
```

### 2. batch_fix_devnotes_metadata.py

**路径**: `tools/maintenance/helpers/batch_fix_devnotes_metadata.py`

**用途**: 批量修复文档元数据（一次性脚本）

**使用方式**:

```bash
python tools/maintenance/helpers/batch_fix_devnotes_metadata.py
```

## 🔄 Git Hooks 更新

`tools/git-hooks/pre-commit` 已更新为优先使用 `sage-dev` 命令：

### 架构检查

**旧方式**:

```bash
python3 "$ROOT_DIR/tools/architecture_checker.py" --root "$ROOT_DIR" --changed-only
```

**新方式**:

```bash
sage-dev check-architecture --changed-only
```

### 文档检查

**旧方式**:

```bash
python3 "$ROOT_DIR/tools/devnotes_checker.py" --root "$ROOT_DIR" --changed-only
```

**新方式**:

```bash
sage-dev check-devnotes --changed-only
```

**向后兼容**: Git hook 会检测 `sage` 命令是否可用，如果不可用则回退到直接调用 Python 脚本。

## 📚 文档更新

已更新以下文档中的命令引用：

1. `docs/dev-notes/architecture/KERNEL_REFACTORING_ANALYSIS_1041.md`
1. `docs/dev-notes/ci-cd/DOCUMENTATION_MAINTENANCE_QUICKREF.md`
1. `docs/dev-notes/ci-cd/DOCUMENTATION_CHECK_REPORT.md`
1. `docs/dev-notes/ci-cd/PACKAGE_README_GUIDELINES.md`
1. `docs/dev-notes/ci-cd/PACKAGE_README_QUALITY_REPORT.md`

所有 `python tools/xxx_checker.py` 引用都已更新为 `sage-dev check-xxx`。

## 💡 使用指南

### 快速开始

```bash
# 安装 sage-tools（如果还没安装）
pip install -e packages/sage-tools

# 运行所有质量检查
sage-dev quality

# 只运行特定检查
sage-dev check-architecture
sage-dev check-devnotes
sage-dev check-readme
```

### 集成到工作流

```bash
# 提交前运行所有检查
sage-dev quality --all-files

# 只检查变更的文件（更快）
sage-dev quality

# CI/CD 中使用
sage-dev quality --all-files --no-fix
```

### 开发调试

```bash
# 详细模式
sage-dev check-architecture --verbose
sage-dev check-devnotes --verbose

# 仅警告模式（不中断）
sage-dev quality --warn-only
```

## 🔍 技术细节

### 模块导出

`packages/sage-tools/src/sage/tools/dev/tools/__init__.py`:

```python
from .architecture_checker import ArchitectureChecker
from .devnotes_checker import DevNotesChecker
from .package_readme_checker import PackageREADMEChecker
```

### CLI 命令

`packages/sage-tools/src/sage/tools/cli/commands/dev/main.py`:

- `@app.command() def check_architecture(...)` - 架构检查
- `@app.command() def check_devnotes(...)` - 文档检查
- `@app.command() def check_readme(...)` - README 检查
- `@app.command() def quality(...)` - 集成所有检查

### Quality 命令选项

```python
sage-dev quality \
    --architecture/--no-architecture  # 架构检查（默认启用）
    --devnotes/--no-devnotes          # 文档检查（默认启用）
    --readme                          # README 检查（默认禁用）
    --all-files                       # 检查所有文件
    --warn-only                       # 只警告不中断
```

## 🎯 迁移完成

- ✅ `architecture_checker.py` → `sage-dev check-architecture`
- ✅ `devnotes_checker.py` → `sage-dev check-devnotes`
- ✅ `package_readme_checker.py` → `sage-dev check-readme`
- ✅ Git hooks 更新为使用新命令
- ✅ 文档引用全部更新
- ✅ 辅助工具移动到 `tools/maintenance/helpers/`

## 📋 待办事项

- [ ] 为新命令添加单元测试
- [ ] 更新 CI/CD 流程使用新命令
- [ ] 在 sage-tools README 中添加使用说明
- [ ] 考虑添加 `sage-dev check-all` 命令作为快捷方式

## 🔗 相关文档

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 项目结构指南
- [PACKAGE_ARCHITECTURE.md](../../PACKAGE_ARCHITECTURE.md) - 包架构规范
- [DOCUMENTATION_MAINTENANCE_QUICKREF.md](../ci-cd/DOCUMENTATION_MAINTENANCE_QUICKREF.md) - 文档维护快速参考

______________________________________________________________________

**迁移日期**: 2025-10-26\
**版本**: v1.0\
**状态**: ✅ 已完成
