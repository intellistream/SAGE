# SAGE Maintenance Tools

本目录包含 SAGE 项目的维护和工具脚本。

This directory contains various maintenance and utility scripts for the SAGE project.

## � 快速开始

### 使用主脚本（推荐）

所有维护功能都已整合到 `sage-maintenance.sh` 主脚本中：

```bash
# 显示帮助
./tools/maintenance/sage-maintenance.sh --help

# 运行健康检查
./tools/maintenance/sage-maintenance.sh doctor

# 查看项目状态
./tools/maintenance/sage-maintenance.sh status

# Submodule 管理
./tools/maintenance/sage-maintenance.sh submodule status
./tools/maintenance/sage-maintenance.sh submodule switch
./tools/maintenance/sage-maintenance.sh submodule fix-conflict

# 清理项目
./tools/maintenance/sage-maintenance.sh clean
./tools/maintenance/sage-maintenance.sh clean-deep

# 安全检查
./tools/maintenance/sage-maintenance.sh security-check

# 设置 Git hooks
./tools/maintenance/sage-maintenance.sh setup-hooks
```

## 📁 目录结构

```
tools/maintenance/
├── sage-maintenance.sh          # 🌟 主脚本 - 统一入口
├── setup_hooks.sh               # Git hooks 安装脚本
├── sage-jobmanager.sh           # Job 管理工具（特定服务）
├── README.md                    # 本文档
├── git-hooks/                   # Git 钩子模板
│   └── post-checkout           # 自动切换 submodule 分支
└── helpers/                     # 辅助脚本（内部使用）
    ├── common.sh               # 通用函数库
    ├── manage_submodule_branches.sh
    ├── resolve_submodule_conflict.sh
    ├── cleanup_old_submodules.sh
    ├── prepare_branch_checkout.sh
    ├── quick_cleanup.sh
    └── check_config_security.sh
```

## 📚 主要功能

### 🔄 Submodule 管理

```bash
# 查看 submodule 状态
./tools/maintenance/sage-maintenance.sh submodule status

# 切换 submodule 分支（根据当前 SAGE 分支）
./tools/maintenance/sage-maintenance.sh submodule switch

# 初始化 submodules
./tools/maintenance/sage-maintenance.sh submodule init

# 更新 submodules
./tools/maintenance/sage-maintenance.sh submodule update

# 解决 submodule 冲突
./tools/maintenance/sage-maintenance.sh submodule fix-conflict

# 清理旧的 submodule 配置
./tools/maintenance/sage-maintenance.sh submodule cleanup
```

### 🧹 项目清理

```bash
# 标准清理（构建产物、缓存等）
./tools/maintenance/sage-maintenance.sh clean

# 深度清理（包括 Python 缓存、日志等）
./tools/maintenance/sage-maintenance.sh clean-deep
```

### 🛡️ 安全检查

```bash
# 检查配置文件中的敏感信息（API keys 等）
./tools/maintenance/sage-maintenance.sh security-check
```

### 🔧 Git Hooks

```bash
# 安装/重新安装 Git hooks
./tools/maintenance/sage-maintenance.sh setup-hooks

# 强制覆盖现有 hooks
./tools/maintenance/sage-maintenance.sh setup-hooks -f
```

### 🔍 诊断工具

```bash
# 运行完整的健康检查
./tools/maintenance/sage-maintenance.sh doctor

# 显示项目状态概览
./tools/maintenance/sage-maintenance.sh status
```

## 🎯 开发模式（推荐）

开发模式下，`quickstart.sh` 会**自动**设置 Git hooks：

```bash
# 安装 SAGE（开发模式）
./quickstart.sh --dev --yes

# ✅ Git hooks 会自动设置，无需手动操作
# ✅ 以后每次切换分支，submodules 会自动跟随切换
```


## 📚 详细说明

### 当前 Submodule 结构

重构后的 submodule 路径（2025年10月更新）：

```
packages/sage-middleware/src/sage/middleware/components/
├── sage_db/
│   └── sageDB/          # ← Submodule
├── sage_flow/
│   └── sageFlow/        # ← Submodule
└── sage_vllm/
    └── sageLLM/         # ← Submodule

docs-public/             # ← Submodule
```

**重要变更**：`sage_db` 和 `sage_flow` 本身不再是 submodules，而是包含 submodules 的目录。实际的 submodules 下沉到了 `sageDB` 和 `sageFlow` 子目录中。

### Submodule 自动管理机制

SAGE 项目使用 Git hooks 实现 submodule 的自动管理：

1. **安装阶段**（quickstart.sh --dev）
   - 自动运行 `setup_hooks.sh`
   - 安装 `post-checkout` hook 到 `.git/hooks/`

2. **切换分支时**（自动）
   - Git hook 自动调用 `helpers/manage_submodule_branches.sh`
   - 根据当前分支切换 submodules：
     - `main` 分支 → submodules 的 `main` 分支
     - 其他分支 → submodules 的 `main-dev` 分支

3. **好处**
   - ✅ 自动化，无需手动管理
   - ✅ 避免 submodule 版本冲突
   - ✅ 保持分支间的一致性

### 脚本架构

- **sage-maintenance.sh**: 主脚本，提供统一的用户界面
- **helpers/**: 内部辅助脚本，不建议直接调用
  - `common.sh`: 通用函数库
  - `manage_submodule_branches.sh`: Submodule 分支管理核心逻辑
  - `resolve_submodule_conflict.sh`: 冲突解决工具
  - `cleanup_old_submodules.sh`: 清理旧配置
  - `quick_cleanup.sh`: 项目清理工具
  - `check_config_security.sh`: 安全检查工具
- **git-hooks/**: Git 钩子模板
  - `post-checkout`: 分支切换后自动执行

## ⚠️ 注意事项

1. **优先使用主脚本**: 使用 `sage-maintenance.sh` 而不是直接调用 helpers 中的脚本
2. **自动化优先**: 开发模式下使用 Git hooks，避免手动管理
3. **分支规范**: 遵循 main/main-dev 分支命名规范
4. **路径更新**: 使用新的 submodule 路径（sageDB, sageFlow 在子目录中）
5. **清理习惯**: 定期运行清理命令保持环境整洁

## 📖 相关文档

- [CI/CD 文档](../../docs/ci-cd/README.md)
- [开发者快捷命令](../../docs/dev-notes/DEV_COMMANDS.md)

## 🆘 常见问题

**Q: submodule 没有自动切换怎么办？**

A: 运行健康检查并按提示操作：
```bash
./tools/maintenance/sage-maintenance.sh doctor
```

**Q: 遇到 "refusing to create/use in another submodule's git dir" 错误？**

A: 这是旧配置冲突，运行清理：
```bash
./tools/maintenance/sage-maintenance.sh submodule cleanup
```

**Q: 如何查看所有可用命令？**

A: 查看帮助信息：
```bash
./tools/maintenance/sage-maintenance.sh --help
```

**Q: 可以禁用自动 submodule 管理吗？**

A: 可以，删除 hook 文件：
```bash
rm .git/hooks/post-checkout
```

**Q: 如何查看 submodule 当前状态？**

A: 使用状态命令：
```bash
./tools/maintenance/sage-maintenance.sh submodule status
# 或查看整体状态
./tools/maintenance/sage-maintenance.sh status
```

**Q: helpers 目录下的脚本可以直接运行吗？**

A: 可以，但不推荐。建议通过主脚本 `sage-maintenance.sh` 调用，这样能获得更好的错误处理和用户体验。

---

💡 **提示**: 大多数情况下，使用 `sage-maintenance.sh doctor` 和 `sage-maintenance.sh status` 就能诊断和解决常见问题。


