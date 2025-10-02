# ✅ Submodule 分支管理系统实现总结

## 🎯 实现目标

创建一个智能的 submodule 分支管理系统：
- **SAGE 在 `main` 分支** → submodules 使用 `main` 分支
- **SAGE 在其他分支**（如 `main-dev`）→ submodules 使用 `main-dev` 分支

## 📦 实现内容

### 1. 核心脚本：`tools/maintenance/manage_submodule_branches.sh`

**功能**：
- ✅ 自动检测当前 SAGE 分支
- ✅ 根据规则切换 submodules 到对应分支
- ✅ 更新 `.gitmodules` 配置
- ✅ 显示当前状态

**命令**：
```bash
# 切换 submodules（根据当前 SAGE 分支自动判断）
./tools/maintenance/manage_submodule_branches.sh switch

# 查看当前状态
./tools/maintenance/manage_submodule_branches.sh status

# 查看帮助
./tools/maintenance/manage_submodule_branches.sh help
```

### 2. 自动化 Hook：`tools/maintenance/git-hooks/post-checkout`

**功能**：
- ✅ 在切换 SAGE 分支时自动触发
- ✅ 自动运行 `switch` 命令同步 submodules
- ✅ 无需手动干预

**效果**：
```bash
# 切换分支会自动同步 submodules
git checkout main-dev
# 🔄 检测到分支切换，自动同步 submodule 分支...

# 安装一次即可自动生效
cp tools/maintenance/git-hooks/post-checkout .git/hooks/post-checkout
chmod +x .git/hooks/post-checkout
```

### 3. 详细文档：`docs/SUBMODULE_BRANCH_MANAGEMENT.md`

**内容**：
- ✅ 系统概述和设计目标
- ✅ 快速开始指南
- ✅ 详细命令说明
- ✅ 工作流程示例
- ✅ 故障排查指南
- ✅ CI/CD 集成说明

## 🔑 关键设计决策

### ✨ 不自动创建分支

**原因**：
1. Submodules 的 `main` 和 `main-dev` 分支应该在各自仓库中独立维护
2. 自动创建会导致分支关系混乱（不应该将 main-dev 基于 main 创建）
3. 给予开发者更多控制权

**解决方案**：
- 脚本只负责**切换（checkout）**已有分支
- 需要手动在 submodule 仓库创建和维护分支

### 🎨 简洁的命令接口

**设计**：
- 默认命令就是 `switch`
- 只保留必要的命令：`switch`、`status`、`help`
- 移除了 `create-maindev` 命令

**好处**：
- 更直观易用
- 减少混淆
- 符合 Unix 哲学：做好一件事

## 📊 工作流程

### 场景 1：开发新功能

```bash
# 1. 切换到开发分支（自动同步 submodules）
git checkout main-dev

# 2. 确认状态
./tools/maintenance/manage_submodule_branches.sh status

# 3. 提交 .gitmodules 更改
git add .gitmodules
git commit -m "chore: switch submodules to main-dev"

# 4. 开始开发...
```

### 场景 2：准备发布

```bash
# 1. 切换到 main 分支（自动同步 submodules）
git checkout main

# 2. 合并开发分支
git merge main-dev

# 3. 提交并推送
git push origin main
```

### 场景 3：查看当前状态

```bash
./tools/maintenance/manage_submodule_branches.sh status
```

输出示例：
```
🚀 SAGE Submodule 状态
SAGE 分支: main-dev

Submodule 配置：
Submodule                                          配置分支    当前分支   
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docs-public                                        main-dev    main-dev       
sage_flow                                          main-dev    main-dev       
sage_db                                            main-dev    main-dev       
```

## 🔧 技术实现细节

### 分支判断逻辑

```bash
if [ "$current_branch" = "main" ]; then
    target_branch="main"
else
    target_branch="main-dev"
fi
```

### Submodule 切换

```bash
# 进入 submodule 目录
cd "$submodule_path"

# 获取远程分支
git fetch origin

# 切换到目标分支
git checkout -B "$target_branch" "origin/$target_branch"
```

### .gitmodules 更新

```bash
git config --file .gitmodules "submodule.${submodule_path}.branch" "$target_branch"
```

## ⚠️ 重要提醒

### 前置条件

1. ✅ 所有 submodules 远程仓库必须已有 `main` 和 `main-dev` 分支
2. ✅ 确保有访问这些分支的权限
3. ✅ Submodules 需要已初始化

### 手动操作场景

在以下情况下需要手动处理：
1. **Submodule 分支不存在**：需要在对应仓库创建
2. **权限不足**：需要联系仓库维护者
3. **本地有未提交更改**：需要先处理 submodule 的更改

## 📝 提交信息

### Fix 分支（libstdc++ 修复）

```
commit 97a9ce92
fix: skip libstdc++ check in pip/system environments (#869)

- Add install_environment parameter to ensure_libstdcxx_compatibility
- Skip libstdc++ check when using pip or system Python
- Update main_installer.sh to pass environment parameter
- Eliminate misleading warnings in CI environment

Fixes #869
```

### Main-dev 分支（Submodule 管理系统）

```
commit b698b484
feat: add dynamic submodule branch management system

- Add tools/maintenance/manage_submodule_branches.sh script
- Automatically switch submodules based on SAGE branch:
  * main branch → submodules use main branch
  * other branches → submodules use main-dev branch
- Add Git post-checkout hook for automatic synchronization
- Add comprehensive documentation in docs/SUBMODULE_BRANCH_MANAGEMENT.md
- Update .gitmodules automatically when switching branches

This system enables:
- Clean separation between stable (main) and development (main-dev) code
- Automatic branch synchronization when switching SAGE branches
- Easy status checking and manual control when needed
```

## 🚀 下一步行动

### 1. 推送到远程

```bash
# 推送 fix 分支
git push origin fix/libstdcxx-ci-check-869

# 推送 main-dev（包含两个改动）
git push origin main-dev
```

### 2. 创建 Pull Requests

**PR 1: Fix #869 - libstdc++ CI Check**
- 从 `fix/libstdcxx-ci-check-869` 到 `main-dev`
- 修复 CI 环境中的 libstdc++ 检查误导性警告

**PR 2: Submodule Branch Management**
- 从 `main-dev` 到 `main`（如果准备发布）
- 或保持在 `main-dev` 继续开发

### 3. 在 Submodule 仓库创建 main-dev 分支

对于每个 submodule：
```bash
# sageDB
cd packages/sage-middleware/src/sage/middleware/components/sage_db
git checkout main
git checkout -b main-dev
git push -u origin main-dev

# sageFlow
cd ../sage_flow
git checkout main
git checkout -b main-dev
git push -u origin main-dev

# SAGE-Pub
cd ../../../../../../../../docs-public
git checkout main
git checkout -b main-dev
git push -u origin main-dev
```

### 4. 测试完整流程

```bash
# 1. 确保 submodules 分支已创建
./tools/maintenance/manage_submodule_branches.sh status

# 2. 测试切换到 main
git checkout main

# 3. 测试切换到 main-dev
git checkout main-dev

# 4. 验证 submodules 正确切换
./tools/maintenance/manage_submodule_branches.sh status
```

## 💡 使用建议

### 团队协作

1. **统一使用脚本**：团队成员都应使用此脚本管理 submodules
2. **提交 .gitmodules**：每次切换后提交 `.gitmodules` 的更改
3. **CI 集成**：在 CI 配置中使用此脚本初始化 submodules

### CI/CD 配置

```yaml
- name: Initialize Submodules
  run: |
    # 根据分支自动切换 submodules
    ./tools/maintenance/manage_submodule_branches.sh switch
    
    # 初始化并更新
    git submodule update --init --recursive
```

## 📚 相关文档

- [完整文档](../docs/SUBMODULE_BRANCH_MANAGEMENT.md)
- [Git Submodules 官方文档](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [Issue #869](https://github.com/intellistream/SAGE/issues/869)

---

**总结**：✅ 两个功能都已完整实现并提交到对应分支，可以推送和创建 PR 了！
