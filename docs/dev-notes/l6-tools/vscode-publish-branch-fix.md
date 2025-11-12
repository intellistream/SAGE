# VS Code "Publish Branch" 问题解决方案

**Date**: 2024-11-12  
**Author**: SAGE Development Team  
**Summary**: 修复浅克隆导致的 submodule 上游追踪缺失问题，解决 VS Code 误显示 "Publish Branch" 的问题

## 问题描述

在使用 `quickstart.sh` 安装 SAGE 后，在 VS Code 的 Source Control 界面中，所有 submodule（包括 libamm）都显示 **"Publish Branch"** 按钮，但实际上这些分支已经存在于远程仓库。

## 根本原因

这是由于 SAGE 的快速安装优化导致的**显示问题**，而非实际的 Git 问题：

### 1. 浅克隆优化

`quickstart.sh` 使用浅克隆（`--depth 1`）来加速 submodule 初始化：
- 减少约 80% 的下载时间和磁盘占用
- 只克隆最近的一次提交

### 2. Git 配置限制

浅克隆时，Git 默认只配置默认分支（通常是 `main`）的 fetch refspec：
```bash
remote.origin.fetch = +refs/heads/main:refs/remotes/origin/main
```

当切换到 `main-dev` 分支时：
- ✅ 分支已正确切换
- ✅ 远程分支存在
- ❌ 但缺少 `main-dev` 的 fetch refspec
- ❌ 没有设置上游追踪（upstream tracking）

### 3. VS Code 的判断逻辑

VS Code 检测到：
- 本地有 `main-dev` 分支
- 但没有上游追踪信息 `[origin/main-dev]`
- 误认为这是一个新的本地分支，需要 "publish"

## 验证方法

### 检查分支追踪状态

```bash
# 进入 submodule 目录
cd packages/sage-libs/src/sage/libs/libamm

# 查看分支信息（-vv 显示上游追踪）
git branch -vv
```

**问题示例：**
```
  main     959fd33 [origin/main] ci: Skip dataset copy in CI workflow
* main-dev e684436 build: use system pybind11
```
注意 `main-dev` **没有** `[origin/main-dev]` 标记。

**修复后：**
```
  main     959fd33 [origin/main] ci: Skip dataset copy in CI workflow
* main-dev e684436 [origin/main-dev] build: use system pybind11
```

### 检查远程分支是否真的存在

```bash
# 验证远程仓库确实有 main-dev 分支
git ls-remote --heads origin main-dev
# 输出：e68443629d88585599899daa5a6262ff131fe777 refs/heads/main-dev

# 查看所有引用
git show-ref
# 应该能看到 refs/remotes/origin/main-dev
```

### 检查 Git 配置

```bash
# 查看 fetch refspec 配置
git config --get-all remote.origin.fetch
```

如果只显示 `+refs/heads/main:refs/remotes/origin/main`，说明缺少 `main-dev` 的配置。

## 解决方案

### 用户快速修复

如果您遇到此问题，只需：

```bash
# 1. 拉取最新代码（包含修复）
git pull

# 2. 运行一次 submodule 切换（自动修复）
./manage.sh submodule switch
```

完成！VS Code 的 "Publish Branch" 按钮应该消失了。

### 技术说明

**最新版本的 SAGE 已自动集成修复**。

`manage.sh submodule switch` 在切换分支时会自动：
1. 为每个 submodule 添加正确的 fetch refspec
2. 设置上游追踪分支
3. 修复 VS Code 显示问题

### 手动修复单个 submodule

如果需要手动修复特定 submodule：

```bash
# 进入问题 submodule
cd packages/sage-libs/src/sage/libs/libamm

# 1. 添加 main-dev 的 fetch refspec
git config --add remote.origin.fetch '+refs/heads/main-dev:refs/remotes/origin/main-dev'

# 2. 重新 fetch
git fetch origin

# 3. 设置上游追踪
git branch -u origin/main-dev main-dev
```

### 全新安装

最新版本的 `quickstart.sh` 会自动调用 `manage.sh`，在初始化 submodule 时自动修复此问题。新用户不会遇到此问题。

## 验证修复

修复后，检查以下内容：

### 1. 分支追踪状态
```bash
cd packages/sage-libs/src/sage/libs/libamm
git branch -vv
```
应该显示 `* main-dev e684436 [origin/main-dev] build: use system pybind11`

### 2. VS Code 界面
- 重启 VS Code 或刷新 Source Control 视图
- "Publish Branch" 按钮应该消失
- 显示同步状态（↑↓）或 ✓ 图标

### 3. Git 状态
```bash
git status
```
应该显示 `On branch main-dev` 和 `Your branch is up to date with 'origin/main-dev'.`

## 常见问题

### Q: 点击 "Publish Branch" 会怎样？

A: 由于远程分支已存在，Git 会提示错误或尝试强制推送。**不建议**点击，使用上述修复方法即可。

### Q: 这会影响实际使用吗？

A: **不会**。这只是 VS Code 的显示问题，不影响：
- Git 命令行操作
- 代码功能
- Submodule 更新
- 提交和推送

### Q: 为什么要使用浅克隆？

A: 性能优化：
- 减少初始下载时间：从 5-10 分钟降至 2-3 分钟
- 节省磁盘空间：约 80% 的空间节省
- 对于日常开发，浅克隆完全够用

### Q: 如何获取完整历史？

A: 如果需要完整的 Git 历史（不推荐）：
```bash
cd packages/sage-libs/src/sage/libs/libamm
git fetch --unshallow
```

### Q: grafted 是什么意思？

A: 这是 Git 对浅克隆的标记，表示历史记录不完整。这是正常的，不影响功能：
```bash
git log --oneline -5
# e684436 (grafted, HEAD -> main-dev, origin/main-dev) build: use system pybind11
```

## 技术细节

### 自动修复的实现

`tools/maintenance/helpers/manage_submodule_branches.sh` 的 `setup_upstream_tracking()` 函数会：

1. **检查是否已有上游追踪**
   ```bash
   git rev-parse --abbrev-ref --symbolic-full-name @{u}
   ```

2. **添加 fetch refspec**（如果缺失）
   ```bash
   git config --add remote.origin.fetch \
     "+refs/heads/$branch:refs/remotes/origin/$branch"
   ```

3. **更新远程引用**
   ```bash
   git fetch origin "$branch"
   ```

4. **设置上游追踪**
   ```bash
   git branch -u "origin/$branch" "$branch"
   ```

### 集成点

该修复已集成到 `switch_submodule_branch()` 函数中，在以下场景自动触发：
- `./manage.sh submodule switch` - 手动切换分支
- `./manage.sh submodule bootstrap` - 初始化 submodule（被 quickstart.sh 调用）
- `./quickstart.sh --sync-submodules` - 快速安装

## 相关资源

- [Git Submodules 文档](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [Git Shallow Clone](https://git-scm.com/docs/git-clone#Documentation/git-clone.txt---depthltdepthgt)
- [Git Branch Tracking](https://git-scm.com/book/en/v2/Git-Branching-Remote-Branches#_tracking_branches)

## 更新日志

- **2024-11-12**: 修复浅克隆导致的上游追踪问题
- **2024-11-12**: 集成上游追踪修复到 `manage_submodule_branches.sh`
- **2024-11-12**: 自动化修复流程，无需独立命令
