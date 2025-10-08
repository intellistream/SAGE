# Pull Request: Reorganize Maintenance Scripts

## 🎯 目标

重构 `tools/maintenance` 维护脚本，解决：
1. 脚本分散，使用不便
2. submodule 路径重构后的遗留问题
3. 缺乏统一的诊断工具

## 📦 主要变更

### 1. 创建统一主脚本 `sage-maintenance.sh`

提供一站式维护工具：

```bash
# 健康检查
./tools/maintenance/sage-maintenance.sh doctor

# Submodule 管理
./tools/maintenance/sage-maintenance.sh submodule status
./tools/maintenance/sage-maintenance.sh submodule cleanup

# 项目清理
./tools/maintenance/sage-maintenance.sh clean
```

**功能**:
- 🔍 自动诊断 (`doctor` 命令)
- 📦 Submodule 管理 (status, switch, cleanup, etc.)
- 🧹 项目清理 (clean, clean-deep)
- 🛡️ 安全检查
- 🔧 Git hooks 管理

### 2. 重组目录结构

```
tools/maintenance/
├── sage-maintenance.sh      # 主脚本（用户入口）
├── setup_hooks.sh
├── README.md               # 精简版文档
├── git-hooks/
└── helpers/                # 内部脚本
    ├── common.sh
    ├── cleanup_old_submodules.sh  # 新增
    └── 其他辅助脚本...
```

**移动**:
- `sage-jobmanager.sh` → `scripts/` (CLI 工具，不属于维护脚本)
- 其他 `*.sh` → `helpers/` (内部实现)

### 3. 新增功能

#### `cleanup_old_submodules.sh`
解决 submodule 重构遗留问题：
```
error: refusing to create/use in another submodule's git dir
```

#### `doctor` 命令
自动检查并提供修复建议：
- Git 仓库状态
- Git Hooks 安装
- Submodules 初始化
- 旧配置残留
- Python 环境
- 构建产物

### 4. Submodule 分支策略

| SAGE 分支 | Submodules 分支 |
|-----------|----------------|
| `main` | `main` (稳定版) |
| 其他分支 | `main-dev` (开发版) |

通过 Git hooks 自动切换，无需手动管理。

### 5. 修复 Submodule 路径

更新所有脚本以适应新结构：

```
旧: packages/.../sage_db/           (submodule)
新: packages/.../sage_db/sageDB/    (submodule 在子目录)
```

## ✅ 测试结果

- ✅ 所有命令正常工作
- ✅ Doctor 成功诊断问题
- ✅ Submodule cleanup 清理旧配置
- ✅ 所有 4 个 submodules 正确初始化
- ✅ Git hooks 路径更新

## 📊 变更统计

- **新增**: sage-maintenance.sh, helpers/common.sh, helpers/cleanup_old_submodules.sh, scripts/README.md
- **修改**: README.md (精简), git-hooks/post-checkout, PR_DESCRIPTION.md
- **移动**: 5个脚本到 helpers/, sage-jobmanager.sh 到 scripts/
- **删除**: 3个冗余文档 (QUICK_REFERENCE.md, REFACTORING_SUMMARY.md, SUBMODULE_STRATEGY.md)

## 🔄 合并后操作

团队成员拉取后如遇问题：

```bash
# 1. 运行诊断
./tools/maintenance/sage-maintenance.sh doctor

# 2. 按提示修复（通常是）
./tools/maintenance/sage-maintenance.sh submodule cleanup
git submodule sync
git submodule update --init --recursive
```

## 📝 向后兼容

- ✅ helpers 中的脚本仍可独立运行
- ✅ Git hooks 自动更新
- ✅ 现有工作流不受影响

---

**分支**: `refactor/maintenance-scripts-unification`  
**目标**: `main-dev`  
**类型**: Refactoring  
**优先级**: Medium
