# 维护脚本重构总结

## 📅 更新日期
2025年10月8日

## 🎯 重构目标
- 整合分散的维护脚本
- 提供统一的用户界面
- 简化脚本结构和维护
- 解决 submodule 路径重构后的遗留问题

## 📂 新的目录结构

```
```
tools/maintenance/
├── sage-maintenance.sh          # 主脚本（用户入口）
├── setup_hooks.sh
├── README.md                    # 更新的用户文档
├── QUICK_REFERENCE.md           # 快速参考卡片
├── REFACTORING_SUMMARY.md       # 重构总结
├── git-hooks/
│   └── post-checkout            # 已更新路径
└── helpers/                     # 内部辅助脚本
    ├── common.sh                # 通用函数库
    ├── manage_submodule_branches.sh
    ├── resolve_submodule_conflict.sh
    ├── cleanup_old_submodules.sh
    ├── prepare_branch_checkout.sh
    ├── quick_cleanup.sh
    └── check_config_security.sh
```
```

## 🆕 主要变更

### 1. 创建统一主脚本 `sage-maintenance.sh`

**优势**：
- 单一入口点，降低用户学习成本
- 统一的错误处理和用户体验
- 自动化的健康检查和诊断
- 彩色输出和友好的提示信息

**主要功能**：
```bash
# Submodule 管理
sage-maintenance.sh submodule status
sage-maintenance.sh submodule switch
sage-maintenance.sh submodule init
sage-maintenance.sh submodule update
sage-maintenance.sh submodule fix-conflict
sage-maintenance.sh submodule cleanup

# 项目维护
sage-maintenance.sh clean
sage-maintenance.sh clean-deep
sage-maintenance.sh security-check
sage-maintenance.sh setup-hooks

# 诊断工具
sage-maintenance.sh doctor
sage-maintenance.sh status
```

### 2. 创建 helpers/ 目录

**目的**：
- 将内部实现细节与用户接口分离
- 保持向后兼容性（脚本仍可独立运行）
- 便于维护和测试

**移动的脚本**：
- `manage_submodule_branches.sh` → `helpers/`
- `resolve_submodule_conflict.sh` → `helpers/`
- `cleanup_old_submodules.sh` → `helpers/` (新增)
- `prepare_branch_checkout.sh` → `helpers/`
- `quick_cleanup.sh` → `helpers/`
- `check_config_security.sh` → `helpers/`

### 3. 新增 `helpers/common.sh` 函数库

**包含内容**：
- 颜色和样式定义
- 日志函数 (log_info, log_success, log_warning, log_error)
- Git 辅助函数 (get_current_branch, is_git_repo, etc.)
- Submodule 辅助函数
- 确认提示和进度显示
- 错误处理工具

### 4. 新增 `cleanup_old_submodules.sh`

**功能**：
- 清理旧的 `sage_db` 和 `sage_flow` submodule 配置
- 删除 `.git/config` 中的旧条目
- 删除 `.git/modules` 中的缓存
- 清理工作目录中的残留文件
- 处理新 submodule 路径的无效状态

**使用场景**：
解决 submodule 重构后的 "refusing to create/use in another submodule's git dir" 错误

### 5. 增强的健康检查 (`doctor` 命令)

**检查项目**：
1. Git 仓库状态
2. Git Hooks 安装情况
3. Submodules 初始化状态
4. 旧 submodule 配置残留
5. Python 环境
6. 构建产物积累

**输出示例**：
```
🚀 SAGE 项目健康检查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 检查 Git 仓库...
   ✅ Git 仓库正常
   当前分支: main-dev

2. 检查 Git Hooks...
   ✅ Git hooks 已安装

3. 检查 Submodules...
   ✅ 所有 submodules 已初始化 (4/4)

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 所有检查通过！项目状态良好。
```

## 🔄 更新的配置文件

### `.git/hooks/post-checkout`
- 更新路径：`tools/maintenance/manage_submodule_branches.sh` → `tools/maintenance/helpers/manage_submodule_branches.sh`

### `README.md`
- 重写为以主脚本为中心
- 添加新的目录结构说明
- 更新所有示例命令
- 添加 FAQ 部分
- 更新 submodule 路径信息（2025年10月）

## 📝 更新的 Submodule 路径

### 旧结构（已废弃）
```
packages/sage-middleware/src/sage/middleware/components/
├── sage_db/           # ← 曾经是 submodule
└── sage_flow/         # ← 曾经是 submodule
```

### 新结构（当前）
```
packages/sage-middleware/src/sage/middleware/components/
├── sage_db/
│   └── sageDB/        # ← Submodule
├── sage_flow/
│   └── sageFlow/      # ← Submodule
└── sage_vllm/
    └── sageLLM/       # ← Submodule

docs-public/           # ← Submodule
```

## 🚀 使用指南

### 快速开始

```bash
# 查看帮助
./tools/maintenance/sage-maintenance.sh --help

# 运行健康检查
./tools/maintenance/sage-maintenance.sh doctor

# 如果有问题，按提示运行建议的命令
```

### 常见问题解决

#### 问题1: Submodule 冲突
```bash
./tools/maintenance/sage-maintenance.sh submodule cleanup
./tools/maintenance/sage-maintenance.sh submodule init
```

#### 问题2: Git hooks 未安装
```bash
./tools/maintenance/sage-maintenance.sh setup-hooks -f
```

#### 问题3: 构建产物过多
```bash
./tools/maintenance/sage-maintenance.sh clean
```

## ✅ 测试结果

所有功能已测试通过：
- ✅ 主脚本帮助信息正常显示
- ✅ Doctor 命令能正确诊断问题
- ✅ Submodule cleanup 成功清理旧配置
- ✅ Submodule init 成功初始化所有 submodules
- ✅ Git hooks 路径更新正确

## 🔮 未来改进方向

1. **交互式模式**：添加交互式菜单，方便不熟悉命令行的用户
2. **自动修复**：doctor 命令发现问题后，提供一键修复选项
3. **日志记录**：记录维护操作历史，便于问题追踪
4. **配置文件**：支持自定义配置，如跳过某些检查
5. **CI/CD 集成**：提供适合 CI/CD 的非交互模式

## 📚 相关文档

- [维护工具 README](README.md)
- [开发者快捷命令](../../docs/dev-notes/DEV_COMMANDS.md)
- [Submodule 管理](../../docs/ci-cd/SUBMODULE_MANAGEMENT.md)

---

**维护者**: SAGE 开发团队  
**最后更新**: 2025-10-08
