# Pull Request: Reorganize Maintenance Scripts with Unified Entry Point

## 🎯 目标

重构 `tools/maintenance` 目录下的维护脚本，解决以下问题：
1. 脚本分散，使用不便
2. submodule 路径重构后的遗留问题（sage_db → sage_db/sageDB, sage_flow → sage_flow/sageFlow）
3. 缺乏统一的诊断和修复工具

## 📦 主要变更

### 1. 创建统一主脚本 `sage-maintenance.sh`

一个功能完整的维护工具，提供：
- 🔍 **诊断工具**: `doctor` 命令自动检查项目健康状态
- 📦 **Submodule 管理**: status, switch, init, update, fix-conflict, cleanup
- 🧹 **项目清理**: clean, clean-deep
- 🛡️ **安全检查**: security-check
- 🔧 **其他工具**: setup-hooks, status

**使用示例**:
```bash
# 运行健康检查（推荐）
./tools/maintenance/sage-maintenance.sh doctor

# Submodule 管理
./tools/maintenance/sage-maintenance.sh submodule status
./tools/maintenance/sage-maintenance.sh submodule cleanup  # 清理旧配置

# 查看帮助
./tools/maintenance/sage-maintenance.sh --help
```

### 2. 重组目录结构

```
tools/maintenance/
├── sage-maintenance.sh          # 🌟 主脚本（用户入口）
├── setup_hooks.sh
├── README.md                    # 重写
├── QUICK_REFERENCE.md           # 新增：快速参考
├── REFACTORING_SUMMARY.md       # 新增：重构文档
├── git-hooks/
│   └── post-checkout            # 更新路径
└── helpers/                     # 新增：内部辅助脚本
    ├── common.sh                # 新增：通用函数库
    ├── cleanup_old_submodules.sh # 新增：清理旧配置
    ├── manage_submodule_branches.sh
    ├── resolve_submodule_conflict.sh
    ├── prepare_branch_checkout.sh
    ├── quick_cleanup.sh
    └── check_config_security.sh
```

**优势**:
- 清晰的用户接口 vs 内部实现分离
- 更好的代码组织和可维护性
- 保持向后兼容（helpers 中的脚本仍可独立运行）

### 3. 新增工具和功能

#### `cleanup_old_submodules.sh`
解决 submodule 重构后的遗留问题：
- 清理 `.git/config` 中的旧 submodule 配置
- 删除 `.git/modules` 中的旧缓存
- 处理工作目录中的残留文件

**解决的错误**:
```
error: submodule git dir '...sage_db/sageDB' is inside git dir '...sage_db'
fatal: refusing to create/use '...sageDB' in another submodule's git dir
```

#### `common.sh` 函数库
提供可复用的工具函数：
- 日志函数（log_info, log_success, log_warning, log_error）
- Git 辅助函数
- Submodule 辅助函数
- 用户交互函数

#### `doctor` 命令
自动检查：
1. Git 仓库状态
2. Git Hooks 安装情况
3. Submodules 初始化状态
4. 旧 submodule 配置残留
5. Python 环境
6. 构建产物积累

并提供修复建议。

### 4. 更新文档

- **README.md**: 以 `sage-maintenance.sh` 为中心重写，添加新的使用方式
- **QUICK_REFERENCE.md**: 快速命令参考卡片
- **REFACTORING_SUMMARY.md**: 详细的重构说明和设计文档

### 5. 修复 Submodule 路径问题

更新所有脚本以适应新的 submodule 结构：

**旧结构**（已废弃）:
```
packages/sage-middleware/src/sage/middleware/components/
├── sage_db/           # ← 曾经是 submodule
└── sage_flow/         # ← 曾经是 submodule
```

**新结构**（当前）:
```
packages/sage-middleware/src/sage/middleware/components/
├── sage_db/
│   └── sageDB/        # ← Submodule
├── sage_flow/
│   └── sageFlow/      # ← Submodule
└── sage_vllm/
    └── sageLLM/       # ← Submodule
```

## ✅ 测试结果

所有功能已测试通过：
- ✅ 主脚本所有命令正常工作
- ✅ Doctor 命令成功诊断问题并提供修复建议
- ✅ Submodule cleanup 成功清理旧配置
- ✅ 所有 4 个 submodules 正确初始化
- ✅ Git hooks 路径更新正确

## 📊 影响范围

### 添加的文件
- `tools/maintenance/sage-maintenance.sh`
- `tools/maintenance/helpers/common.sh`
- `tools/maintenance/helpers/cleanup_old_submodules.sh`
- `tools/maintenance/QUICK_REFERENCE.md`
- `tools/maintenance/REFACTORING_SUMMARY.md`

### 修改的文件
- `tools/maintenance/README.md` - 完全重写
- `tools/maintenance/git-hooks/post-checkout` - 更新脚本路径

### 移动的文件
- `*.sh` → `helpers/*.sh`（除了 setup_hooks.sh）
- `sage-jobmanager.sh` → `scripts/sage-jobmanager.sh`（CLI 工具，不属于维护脚本）

### 向后兼容性
- ✅ 所有 helpers 中的脚本仍可独立运行
- ✅ 现有的 Git hooks 会在下次运行时自动更新
- ✅ 现有文档和引用会在后续 PR 中更新

## 🔄 合并后的操作

团队成员在合并后需要：

1. 拉取最新代码：
```bash
git checkout main-dev
git pull origin main-dev
```

2. 如遇到 submodule 问题，运行：
```bash
./tools/maintenance/sage-maintenance.sh doctor
# 按照提示运行建议的命令
```

3. 或直接运行清理：
```bash
./tools/maintenance/sage-maintenance.sh submodule cleanup
git submodule sync
git submodule update --init --recursive
```

## 📝 后续改进方向

1. 在其他文档中更新对维护脚本的引用
2. 考虑添加交互式菜单模式
3. 集成到 CI/CD 流程中
4. 添加更多自动修复选项

## 🔗 相关 Issues

- 解决 submodule 路径重构后的配置冲突问题
- 改进开发者工具的易用性
- 统一维护脚本接口

## ✅ Checklist

- [x] 代码已测试
- [x] 文档已更新
- [x] 所有脚本有正确的执行权限
- [x] Git hooks 路径已更新
- [x] Submodule 问题已解决
- [x] 向后兼容性已验证

---

**分支**: `refactor/maintenance-scripts-unification`  
**目标分支**: `main-dev`  
**类型**: Refactoring  
**优先级**: Medium
