# SAGE 项目结构规范

**Date**: 2025-10-26 **Author**: sage-development Team **Summary**: Defines the organization
principles for SAGE root directory and development tools, including guidelines for where to place
scripts and configuration files.

## 📁 根目录组织原则

根目录应该**保持简洁**，只包含必要的用户入口和配置文件。

### ✅ 允许在根目录的内容

#### 1. **用户入口脚本**

- `quickstart.sh` - 快速开始/安装脚本
- `manage.sh` - 项目管理脚本
- `Makefile` - 构建工具（C/C++ 组件）

#### 2. **必需的配置文件**

- `codecov.yml` - Codecov 配置（CI/CD 要求在根目录）
- `.gitignore`, `.gitmodules` - Git 配置
- `.env.template` - 环境变量模板

#### 3. **项目文档**

- `README.md` - 项目说明
- `LICENSE` - 许可证
- `CONTRIBUTING.md` - 贡献指南
- `DEVELOPER.md` - 开发者文档

#### 4. **主要目录**

- `packages/` - SAGE 各子包
- `tools/` - 开发和维护工具
- `docs/` - 内部开发文档
- `examples/` - 示例代码
- `.github/` - GitHub 配置和工作流

### ❌ 不允许在根目录的内容

#### 1. **开发脚本** → 移动到 `tools/`

- ❌ `scripts/` 目录已废弃
- ✅ 改用 `tools/dev.sh` - 开发辅助工具
- ✅ 或集成到 `sage-tools` 包中

#### 2. **维护脚本** → 移动到 `tools/maintenance/`

- ❌ 一次性使用的脚本
- ❌ 重构/迁移脚本
- ✅ 改用 `tools/maintenance/` 目录
- ✅ 或 `tools/maintenance/helpers/` 子目录

#### 3. **配置文件** → 移动到 `tools/`

- ❌ 工具特定的配置文件
- ✅ 改用 `tools/pre-commit-config.yaml`
- ✅ 或放在对应工具的目录下

#### 4. **临时文件和日志**

- ❌ `*.log`, `*.tmp`, `*.bak`
- ✅ 应被 `.gitignore` 忽略

## 🛠️ 工具目录结构

```
tools/
├── dev.sh                          # 开发辅助脚本（moved from scripts/）
├── pre-commit-config.yaml          # Pre-commit 配置
├── secrets.baseline                # Secrets 检测基线
├── mypy-wrapper.sh                 # Mypy 包装器
├── *_checker.py                    # 各种检查工具
├── lib/                            # 共享函数库
│   ├── common_utils.sh
│   └── logging.sh
├── maintenance/                    # 维护工具
│   ├── fix-types-helper.sh        # 类型修复助手（moved from scripts/）
│   ├── sage-maintenance.sh        # 主维护脚本
│   └── helpers/                   # 辅助脚本
│       ├── sage-jobmanager.sh    # Job Manager 包装器（moved from scripts/）
│       └── update_ruff_ignore.py  # 一次性工具
├── git-hooks/                     # Git hooks
├── install/                       # 安装相关工具
├── conda/                         # Conda 相关工具
└── templates/                     # 模板文件
```

## 📝 开发者指南

### 如果你想添加新的脚本...

#### 问题 1: 这个脚本是给谁用的？

- **用户使用** → 考虑集成到 `sage-tools` 包
- **开发者使用** → 放到 `tools/` 或子目录

#### 问题 2: 这个脚本的用途是什么？

- **开发工作流**（测试、格式化、检查）→ `tools/dev.sh` 或 `tools/`
- **维护任务**（清理、修复、更新）→ `tools/maintenance/`
- **一次性使用**（迁移、重构）→ `tools/maintenance/helpers/`
- **共享函数库** → `tools/lib/`

#### 问题 3: 这个脚本需要经常运行吗？

- **是** → 考虑集成到 `sage-dev` 命令
- **否** → 放在 `tools/maintenance/helpers/`

### 更新文档引用

如果移动或重命名脚本，请更新：

1. `DEVELOPER.md` - 开发者文档
1. `CONTRIBUTING.md` - 贡献指南
1. `docs/dev-notes/` - 开发笔记
1. `tools/maintenance/sage-maintenance.sh` - 维护脚本引用
1. 其他相关 README 文件

## 🗂️ 历史迁移记录

### 2025-10-26: scripts/ 目录清理

**删除的目录**:

- `scripts/` - 整个目录已移除

**移动的文件**:

- `scripts/dev.sh` → `tools/dev.sh`
- `scripts/fix-types-helper.sh` → `tools/maintenance/fix-types-helper.sh`
- `scripts/sage-jobmanager.sh` → `tools/maintenance/helpers/sage-jobmanager.sh`

**删除的文件**:

- `scripts/kernel_refactoring_batch.sh` - 一次性重构脚本，已完成
- `scripts/common_utils.sh` - 符号链接，不必要
- `scripts/logging.sh` - 符号链接，不必要
- `scripts/README.md` - 目录文档，已过时

**更新的文档**:

- `DEVELOPER.md` - 18 处引用
- `CONTRIBUTING.md` - 3 处引用
- `docs/dev-notes/tools/pre-commit-quick-reference.md` - 7 处引用
- `tools/maintenance/sage-maintenance.sh` - 6 处引用

## 🔗 相关链接

- [开发者文档](../DEVELOPER.md)
- [贡献指南](../CONTRIBUTING.md)
- [工具目录 README](../tools/README.md)
- [维护工具 README](../tools/maintenance/README.md)
