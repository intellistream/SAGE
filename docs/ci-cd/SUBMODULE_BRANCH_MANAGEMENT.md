# SAGE Submodule 分支管理系统

## 📋 概述

本系统实现了 SAGE 主仓库与 submodules 之间的**智能分支同步机制**：

- **main 分支** → submodules 的 `main` 分支
- **其他分支**（如 main-dev）→ submodules 的 `main-dev` 分支

## 🎯 设计目标

1. **开发隔离**：main-dev 分支用于开发，不影响 main 分支的稳定性
2. **自动同步**：切换分支时自动同步 submodule 到对应分支
3. **灵活管理**：提供完整的工具集管理 submodule 分支状态

## 📁 组件结构

```
SAGE/
├── tools/maintenance/git-hooks/post-checkout   # Git hook 示例（可选）
├── .git/hooks/
│   └── post-checkout           # 拷贝示例后启用的 Git hook
├── tools/maintenance/
│   └── manage_submodule_branches.sh  # 主管理脚本
└── .gitmodules                 # Submodule 配置（根据分支不同）
```

## 🚀 快速开始

### 前置条件

确保所有 submodules 的远程仓库已经有 `main` 和 `main-dev` 两个独立的分支。

### 使用方法

#### 切换 SAGE 分支并同步 submodules

```bash
# 切换到 main-dev 分支
git checkout main-dev

# 同步 submodules（自动判断目标分支）
./tools/maintenance/manage_submodule_branches.sh switch
```

或者如果安装了 Git hook，切换分支会自动同步：

```bash
# Git hook 会自动运行 switch 命令
git checkout main-dev
```

#### 提交 .gitmodules 的更改

```bash
# 查看更改
git diff .gitmodules

# 提交更改
git add .gitmodules
git commit -m "chore: update submodules to main-dev branch"
```

## 📖 详细使用指南

### 命令说明

#### 1. 切换 submodule 分支

```bash
./tools/maintenance/manage_submodule_branches.sh switch
```

**功能**：
- 根据当前 SAGE 分支自动判断目标分支
- 更新 .gitmodules 配置
- 切换所有 submodules 到目标分支

**逻辑**：
- SAGE 在 `main` → submodules 切换到 `main`
- SAGE 在其他分支 → submodules 切换到 `main-dev`

**输出示例**：
```
🚀 SAGE Submodule 分支管理
当前 SAGE 分支: main-dev

ℹ️ 在 main-dev 分支，submodules 将切换到 main-dev 分支

📦 处理 submodule: SAGE-Pub
  当前配置分支: stable
  目标分支: main-dev
  切换到 main-dev 分支...
  ✅ 已切换到 main-dev

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 成功: 3
```

#### 2. 查看状态

```bash
./tools/maintenance/manage_submodule_branches.sh status
```

**功能**：
- 显示当前 SAGE 分支
- 列出所有 submodules 的配置分支和实际分支
- 高亮不一致的情况

**输出示例**：
```
🚀 SAGE Submodule 状态
SAGE 分支: main-dev

Submodule 配置：
Submodule                                          配置分支         当前分支        
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docs-public                                        main-dev        main-dev       
sageFlow                                           main-dev        main-dev       
sageDB.git                                         main-dev        main-dev       
```

## 🔧 Git Hook 自动同步（可选）

### 安装 Git Hook

仓库提供示例脚本 `tools/maintenance/git-hooks/post-checkout`，推荐通过 helper 一键安装：

```bash
./tools/maintenance/setup_hooks.sh
```

如需覆盖已存在的 hook，可追加 `--force`。也可以手动复制：

```bash
cp tools/maintenance/git-hooks/post-checkout .git/hooks/post-checkout
chmod +x .git/hooks/post-checkout
```

### 验证 Hook

```bash
# 检查 hook 是否存在且可执行
ls -la .git/hooks/post-checkout

# 测试：切换分支应自动同步
git checkout main
# 应该看到自动同步的输出
```

### 禁用 Hook

如果不需要自动同步，删除或重命名 hook：

```bash
mv .git/hooks/post-checkout .git/hooks/post-checkout.disabled
```

## 🧹 切换前清理缺失的 Submodule

当目标分支（如 `main`）不再跟踪某些 submodule 时，直接 `git checkout` 可能因为本地仍保留旧的子模块目录而失败。使用辅助脚本可在切换前自动清理：

```bash
# 例如准备切换到 main 分支
./tools/maintenance/prepare_branch_checkout.sh main
```

脚本会依次完成：

1. 对比当前 `.gitmodules` 与目标分支的 `.gitmodules`；
2. 自动执行 `git submodule deinit -f` 并删除目标分支不再需要的子模块目录；
3. 执行 `git checkout <target>`；
4. 调用 `manage_submodule_branches.sh switch`，确保切换后子模块状态正确。

> 如果目标分支同样跟踪所有现有子模块，脚本不会删除任何目录，可安全重复执行。

## 📋 工作流程示例

### 场景 1：开始新功能开发

```bash
# 1. 切换到开发分支
git checkout main-dev

# 2. 同步 submodules（如果没有 Git hook）
./tools/maintenance/manage_submodule_branches.sh switch

# 3. 提交 .gitmodules 更改
git add .gitmodules
git commit -m "chore: switch submodules to main-dev"

# 4. 开始开发
# submodules 现在都在 main-dev 分支
```

### 场景 2：准备发布到 main

```bash
# 1. 确保 main-dev 的改动都已提交
git status

# 2. 切换到 main 分支
git checkout main

# 3. 同步 submodules 到 main 分支
./tools/maintenance/manage_submodule_branches.sh switch

# 4. 合并 main-dev 的改动
git merge main-dev

# 5. 提交并推送
git push origin main
```

### 场景 3：创建功能分支

```bash
# 1. 从 main-dev 创建功能分支
git checkout -b feature/new-feature main-dev

# 2. Submodules 会自动使用 main-dev 分支
./tools/maintenance/manage_submodule_branches.sh status

# 3. 开发完成后合并回 main-dev
git checkout main-dev
git merge feature/new-feature
```

## 🎓 高级用法

### 手动更新单个 submodule

```bash
# 进入 submodule 目录
cd packages/sage-middleware/src/sage/middleware/components/sage_flow

# 切换分支
git checkout main-dev

# 拉取最新代码
git pull origin main-dev

# 返回主仓库
cd -

# 提交 submodule 引用更新
git add packages/sage-middleware/src/sage/middleware/components/sage_flow
git commit -m "chore: update sage_flow submodule"
```

### 批量更新所有 submodules

```bash
# 更新所有 submodules 到各自分支的最新代码
git submodule update --remote --merge

# 或者使用脚本先切换再更新
./tools/maintenance/manage_submodule_branches.sh switch
git submodule update --remote --merge
```

### 在 CI/CD 中使用

```yaml
# GitHub Actions 示例
- name: Initialize Submodules
  run: |
    # 根据分支自动切换 submodules
    ./tools/maintenance/manage_submodule_branches.sh switch
    
    # 初始化并更新
    git submodule update --init --recursive
```

## 🔍 故障排查

### 问题 1：Submodule 分支不一致

**症状**：`status` 命令显示配置分支和实际分支不同

**解决**：
```bash
# 重新同步
./tools/maintenance/manage_submodule_branches.sh switch
```

### 问题 2：Submodule 未初始化

**症状**：执行命令时提示 "Submodule 未初始化"

**解决**：
```bash
# 初始化所有 submodules
git submodule update --init --recursive

# 然后重新运行命令
./tools/maintenance/manage_submodule_branches.sh switch
```

### 问题 3: 远程分支不存在

**症状**：`switch` 命令失败，提示"远程分支 main-dev 不存在"

**解决**：
```bash
# 确认 submodule 远程仓库是否有 main-dev 分支
cd packages/sage-middleware/src/sage/middleware/components/sage_flow
git fetch origin
git branch -r | grep main-dev

# 如果没有，需要在 submodule 远程仓库手动创建
# 或联系仓库维护者添加该分支
```

### 问题 4：.gitmodules 冲突

**症状**：合并分支时 .gitmodules 出现冲突

**解决**：
```bash
# 1. 解决冲突（选择正确的分支配置）
git checkout --ours .gitmodules    # 使用当前分支的配置
# 或
git checkout --theirs .gitmodules  # 使用合并分支的配置

# 2. 重新同步
./tools/maintenance/manage_submodule_branches.sh switch

# 3. 完成合并
git add .gitmodules
git commit
```

## 📊 .gitmodules 配置示例

### main 分支的 .gitmodules

```gitmodules
[submodule "docs-public"]
	path = docs-public
	url = https://github.com/intellistream/SAGE-Pub.git
	branch = main

[submodule "packages/sage-middleware/src/sage/middleware/components/sage_flow"]
	path = packages/sage-middleware/src/sage/middleware/components/sage_flow
	url = https://github.com/intellistream/sageFlow
	branch = main

[submodule "packages/sage-middleware/src/sage/middleware/components/sage_db"]
	path = packages/sage-middleware/src/sage/middleware/components/sage_db
	url = https://github.com/intellistream/sageDB.git
	branch = main
```

### main-dev 分支的 .gitmodules

```gitmodules
[submodule "docs-public"]
	path = docs-public
	url = https://github.com/intellistream/SAGE-Pub.git
	branch = main-dev

[submodule "packages/sage-middleware/src/sage/middleware/components/sage_flow"]
	path = packages/sage-middleware/src/sage/middleware/components/sage_flow
	url = https://github.com/intellistream/sageFlow
	branch = main-dev

[submodule "packages/sage-middleware/src/sage/middleware/components/sage_db"]
	path = packages/sage-middleware/src/sage/middleware/components/sage_db
	url = https://github.com/intellistream/sageDB.git
	branch = main-dev
```

## ⚠️ 注意事项

1. **首次设置**：需要先运行 `create-maindev` 创建所有 submodule 的 main-dev 分支

2. **分支推送权限**：确保你有所有 submodule 仓库的推送权限

3. **.gitmodules 提交**：切换分支后记得提交 .gitmodules 的更改

4. **团队协作**：团队成员都应使用此脚本保持一致

5. **CI/CD 环境**：在 CI 配置中也要使用此脚本初始化 submodules

## 🔗 相关命令参考

```bash
# 查看所有 submodules
git submodule status

# 更新 submodules 到最新
git submodule update --remote

# 查看 submodule 差异
git diff --submodule

# 递归推送（包括 submodules）
git push --recurse-submodules=on-demand
```

## 📚 更多资源

- [Git Submodules 官方文档](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [SAGE 项目文档](../docs/)
- [Submodule 管理最佳实践](./SUBMODULE_MANAGEMENT.md)

## 🤝 贡献

如果你发现问题或有改进建议，请：
1. 在主仓库创建 Issue
2. 提交 Pull Request
3. 联系维护团队

---

**维护者**：SAGE 开发团队  
**最后更新**：2025-10-02
