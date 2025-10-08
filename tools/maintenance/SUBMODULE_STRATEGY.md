# Submodule 分支管理策略

## 📋 分支切换规则

### 自动切换逻辑

SAGE 项目通过 Git hooks 和维护脚本自动管理 submodule 分支：

| SAGE 主仓库分支 | Submodules 切换到 | 说明 |
|----------------|------------------|------|
| `main` | `main` | 生产环境，使用稳定版本 |
| `main-dev` | `main-dev` | 主开发分支 |
| `feature/*` | `main-dev` | 功能分支，使用开发版 |
| `refactor/*` | `main-dev` | 重构分支，使用开发版 |
| `fix/*` | `main-dev` | 修复分支，使用开发版 |
| 其他任何分支 | `main-dev` | 默认使用开发版 |

### 核心代码

在 `tools/maintenance/helpers/manage_submodule_branches.sh`:

```bash
if [ "$current_branch" = "main" ]; then
    target_branch="main"
    # SAGE 在 main 分支 → submodules 切换到 main
else
    target_branch="main-dev"
    # SAGE 在其他分支 → submodules 切换到 main-dev
fi
```

## 🔄 工作流程

### 自动化（推荐）

通过 Git hooks 自动管理：

```bash
# 1. 安装 hooks（开发模式自动完成）
./quickstart.sh --dev

# 2. 切换分支时自动同步 submodules
git checkout main       # → submodules 自动切到 main
git checkout main-dev   # → submodules 自动切到 main-dev
```

### 手动管理

如果需要手动控制：

```bash
# 查看当前状态
./tools/maintenance/sage-maintenance.sh submodule status

# 手动切换 submodules（根据当前 SAGE 分支）
./tools/maintenance/sage-maintenance.sh submodule switch
```

## 📦 Submodule 列表

当前 SAGE 项目的 submodules：

1. **docs-public** - 公开文档
   - 仓库: `intellistream/SAGE-Pub`
   - 路径: `docs-public/`

2. **sageDB** - 数据库组件
   - 仓库: `intellistream/sageDB`
   - 路径: `packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB/`

3. **sageFlow** - 工作流引擎
   - 仓库: `intellistream/sageFlow`
   - 路径: `packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow/`

4. **sageLLM** - LLM 服务
   - 仓库: `intellistream/sageLLM`
   - 路径: `packages/sage-middleware/src/sage/middleware/components/sage_vllm/sageLLM/`

## 🎯 设计原理

### 为什么只有 main 特殊？

1. **简化管理**: 只有一个特殊情况，其他都统一
2. **安全优先**: 生产环境（main）使用经过验证的稳定版本
3. **开发灵活**: 所有开发工作都在 main-dev 上进行
4. **一致性**: 避免开发分支之间的 submodule 版本差异

### 实际场景

**场景 1: 新功能开发**
```bash
git checkout -b feature/new-feature main-dev
# ✅ Submodules 自动使用 main-dev
# 开发时与主开发分支保持一致
```

**场景 2: 生产发布**
```bash
git checkout main
# ✅ Submodules 自动切换到稳定的 main 分支
# 确保生产环境使用稳定版本
```

**场景 3: 紧急修复**
```bash
git checkout -b hotfix/critical-fix main-dev
# ✅ Submodules 使用 main-dev
# 修复后合并到 main-dev，然后再发布到 main
```

## 🛠️ 故障排查

### 问题: Submodule 显示为 commit hash 而非分支名

**原因**: Submodule 处于 detached HEAD 状态

**解决**:
```bash
./tools/maintenance/sage-maintenance.sh submodule switch
```

### 问题: Submodule 版本冲突

**原因**: 手动修改了 submodule 版本

**解决**:
```bash
# 方法 1: 重置到配置的分支
./tools/maintenance/sage-maintenance.sh submodule switch

# 方法 2: 手动进入 submodule 调整
cd packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB
git checkout main-dev
git pull origin main-dev
```

### 问题: Git hook 不工作

**原因**: Hooks 未安装或权限问题

**解决**:
```bash
# 重新安装 hooks
./tools/maintenance/sage-maintenance.sh setup-hooks -f
```

## 📚 相关文档

- [维护工具 README](../README.md)
- [快速参考](../QUICK_REFERENCE.md)
- [重构总结](../REFACTORING_SUMMARY.md)

## 🔄 更新历史

- **2025-10-08**: 创建分支管理策略文档
- **2025-10-08**: 修复状态显示逻辑（.git 文件检测）
