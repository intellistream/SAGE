# SAGE Maintenance Tools# SAGE Maintenance Tools



本目录包含 SAGE 项目的维护和工具脚本。This directory contains various maintenance and utility scripts for the SAGE project.



## 📁 脚本分类## Scripts



### 🔄 Submodule 管理（推荐使用）### Submodule Management



| 脚本 | 功能 | 使用场景 |- **`submodule_manager.sh`** - General submodule management utilities

|------|------|----------|- **`submodule_sync.sh`** - Synchronize submodules across different environments

| **`manage_submodule_branches.sh`** | 🌟 **主要工具** - 自动管理 submodule 分支切换 | 切换分支时自动运行 |- **`resolve_submodule_conflict.sh`** - Automatically resolve submodule conflicts during PR merges

| **`setup_hooks.sh`** | 安装 Git hooks（自动调用上述脚本） | quickstart.sh 自动调用 |- **`SUBMODULE_CONFLICT_RESOLUTION.md`** - Comprehensive guide for resolving submodule conflicts

| `resolve_submodule_conflict.sh` | ⚠️ 解决特定冲突 | PR 合并冲突时使用 |

| `prepare_branch_checkout.sh` | 🔧 分支切换准备 | 高级用例 |### System Maintenance



**📦 已废弃（功能已整合）：**- **`quick_cleanup.sh`** - Clean up temporary files and build artifacts

- ~~`submodule_sync.sh`~~ - 功能已整合到 `manage_submodule_branches.sh`- **`sage-jobmanager.sh`** - Job management utilities for SAGE services

- ~~`submodule_manager.sh`~~ - 功能已整合到 `manage_submodule_branches.sh`

## Usage

### 🧹 系统维护

### Resolving Submodule Conflicts

| 脚本 | 功能 |

|------|------|When encountering submodule conflicts during PR merges (especially with `sage_db`):

| **`quick_cleanup.sh`** | 清理临时文件和构建产物 |

| **`check_config_security.sh`** | 检查配置文件中的 API key 泄露 |```bash

| `sage-jobmanager.sh` | Job 管理工具（特定服务） |# Quick resolution using our script

./tools/maintenance/resolve_submodule_conflict.sh

## 🚀 快速开始

# Or manual resolution

### 开发模式（推荐）git checkout --ours packages/sage-middleware/src/sage/middleware/components/sage_db

git submodule update --init --recursive packages/sage-middleware/src/sage/middleware/components/sage_db

开发模式下，`quickstart.sh` 会**自动**设置 Git hooks：git add packages/sage-middleware/src/sage/middleware/components/sage_db

git commit

```bash```

# 安装 SAGE（开发模式）

./quickstart.sh --dev --yesFor detailed instructions, see `SUBMODULE_CONFLICT_RESOLUTION.md`.



# ✅ Git hooks 会自动设置，无需手动操作### General Maintenance

# ✅ 以后每次切换分支，submodules 会自动跟随切换

``````bash

# Clean up build artifacts

### 手动设置 Git Hooks./tools/maintenance/quick_cleanup.sh



如果需要手动设置或重新设置：# Sync submodules

./tools/maintenance/submodule_sync.sh

```bash```

# 安装 post-checkout hook

./tools/maintenance/setup_hooks.sh## Best Practices



# 强制覆盖现有 hook1. Always run maintenance scripts from the project root directory

./tools/maintenance/setup_hooks.sh --force2. Check script permissions before execution: `chmod +x script_name.sh`

```3. Review the documentation before using submodule-related tools

4. Test scripts in a development environment before using in production

### Submodule 分支管理

## Contributing

Git hook 会自动调用，也可以手动运行：

When adding new maintenance tools:

```bash

# 查看当前状态1. Place them in this directory

./tools/maintenance/manage_submodule_branches.sh status2. Update this README with usage instructions

3. Ensure scripts have proper error handling

# 手动切换 submodules（通常不需要）4. Add appropriate documentation
./tools/maintenance/manage_submodule_branches.sh switch
```

### 清理项目

```bash
# 清理构建产物和缓存
./tools/maintenance/quick_cleanup.sh

# 或使用 Makefile
make clean
```

### 安全检查

```bash
# 检查配置文件中的 API key
./tools/maintenance/check_config_security.sh
```

## 📚 详细说明

### Submodule 自动管理机制

SAGE 项目使用 Git hooks 实现 submodule 的自动管理：

1. **安装阶段**（quickstart.sh --dev）
   - 自动运行 `setup_hooks.sh`
   - 安装 `post-checkout` hook 到 `.git/hooks/`

2. **切换分支时**（自动）
   - Git hook 自动调用 `manage_submodule_branches.sh`
   - 根据当前分支切换 submodules：
     - `main` 分支 → submodules 的 `main` 分支
     - 其他分支 → submodules 的 `main-dev` 分支

3. **好处**
   - ✅ 自动化，无需手动管理
   - ✅ 避免 submodule 版本冲突
   - ✅ 保持分支间的一致性

### 解决 Submodule 冲突

PR 合并时如果遇到 submodule 冲突（特别是 `sage_db`）：

```bash
# 使用自动解决脚本
./tools/maintenance/resolve_submodule_conflict.sh

# 或手动解决
git checkout --ours packages/sage-middleware/src/sage/middleware/components/sage_db
git submodule update --init --recursive packages/sage-middleware/src/sage/middleware/components/sage_db
git add packages/sage-middleware/src/sage/middleware/components/sage_db
git commit -m "fix: resolve sage_db submodule conflict"
```

## 🔧 脚本整合计划

为了减少重复和简化维护：

### ✅ 保留（核心功能）
- `manage_submodule_branches.sh` - 主要 submodule 管理工具
- `setup_hooks.sh` - Git hooks 安装
- `quick_cleanup.sh` - 项目清理
- `check_config_security.sh` - 安全检查
- `resolve_submodule_conflict.sh` - 冲突解决（特定场景）
- `prepare_branch_checkout.sh` - 高级分支切换（保留备用）
- `sage-jobmanager.sh` - 特定服务使用

### ❌ 已废弃（建议删除）
- `submodule_sync.sh` - 功能已整合到 `manage_submodule_branches.sh`
- `submodule_manager.sh` - 功能已整合到 `manage_submodule_branches.sh`

## ⚠️ 注意事项

1. **自动化优先**: 开发模式下使用 Git hooks，避免手动管理
2. **分支规范**: 遵循 main/main-dev 分支命名规范
3. **冲突处理**: PR 合并前检查 submodule 状态
4. **清理习惯**: 定期运行 `quick_cleanup.sh` 或 `make clean`

## 📖 相关文档

- [CI/CD 文档](../../docs/ci-cd/README.md)
- [Submodule 管理详解](../../docs/ci-cd/SUBMODULE_MANAGEMENT.md)
- [开发者快捷命令](../../docs/dev-notes/DEV_COMMANDS.md)

## 🆘 常见问题

**Q: submodule 没有自动切换怎么办？**

A: 检查 Git hook 是否安装：
```bash
ls -la .git/hooks/post-checkout
# 如果不存在，运行：
./tools/maintenance/setup_hooks.sh --force
```

**Q: 可以禁用自动 submodule 管理吗？**

A: 可以，删除 hook 文件：
```bash
rm .git/hooks/post-checkout
```

**Q: 如何查看 submodule 当前状态？**

A: 使用以下命令：
```bash
git submodule status
# 或使用管理脚本
./tools/maintenance/manage_submodule_branches.sh status
```

---

💡 **提示**: 大多数情况下，你不需要直接运行这些脚本。开发模式下的自动化机制会处理一切。
