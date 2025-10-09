# SAGE Maintenance Tools

统一的项目维护工具集，提供 Submodule 管理、项目清理、安全检查等功能。

> **注意：** 完整的开发指南请参见：
> - [DEVELOPER.md](../../DEVELOPER.md) - 开发环境设置和 submodule 管理
> - [CONTRIBUTING.md](../../CONTRIBUTING.md) - 贡献指南

## 🚀 快速开始

### 健康检查

```bash
# 运行完整的项目健康检查
./tools/maintenance/sage-maintenance.sh doctor

# 查看所有可用命令
./tools/maintenance/sage-maintenance.sh --help
```

### 常见场景

```bash
# 首次克隆后初始化 submodules
./tools/maintenance/sage-maintenance.sh submodule init

# 切换 SAGE 分支后同步 submodules
git checkout main
./tools/maintenance/sage-maintenance.sh submodule switch

# 检查 submodule 状态
./tools/maintenance/sage-maintenance.sh submodule status

# 清理项目构建产物
./tools/maintenance/sage-maintenance.sh clean
```

## 📋 命令参考

### Submodule 管理

| 命令 | 说明 |
|------|------|
| `submodule init` | 初始化并自动切换到正确分支 |
| `submodule status` | 查看 submodule 状态（带颜色指示） |
| `submodule switch` | 切换 submodule 分支 |
| `submodule update` | 更新到远程最新版本 |
| `submodule fix-conflict` | 解决 submodule 冲突 |
| `submodule cleanup` | 清理旧 submodule 配置 |

### 项目维护

| 命令 | 说明 |
|------|------|
| `doctor` | 运行完整健康检查 |
| `status` | 显示项目状态 |
| `clean` | 清理构建产物 |
| `clean-deep` | 深度清理（包括缓存） |
| `security-check` | 检查敏感信息泄露 |
| `setup-hooks` | 安装 Git hooks |

## 📁 目录结构

```
tools/maintenance/
├── sage-maintenance.sh           # 主脚本（用户入口）
├── setup_hooks.sh               # Git hooks 安装
├── README.md                    # 本文档
├── CHANGELOG.md                 # 更新日志
├── SUBMODULE_GUIDE.md          # Submodule 详细指南
├── git-hooks/                  # Hook 模板
│   └── post-checkout           # 自动切换 submodule 分支
└── helpers/                    # 内部辅助脚本
    ├── common.sh
    ├── manage_submodule_branches.sh
    ├── resolve_submodule_conflict.sh
    ├── cleanup_old_submodules.sh
    ├── quick_cleanup.sh
    └── check_config_security.sh
```

## 🔧 Submodule 分支管理

### 分支匹配规则

| SAGE 分支 | Submodule 分支 | 说明 |
|-----------|---------------|------|
| `main` | `main` | 稳定版本 |
| `main-dev` | `main-dev` | 开发版本 |
| 其他分支 | `main-dev` | 默认开发 |

### 颜色状态说明

运行 `submodule status` 时的颜色含义：

- 🟢 **绿色**：配置分支和当前分支一致（正常）
- 🟡 **黄色**：配置分支与当前分支不一致
- 🔴 **红色**：处于 detached HEAD 状态（需要修复）
./quickstart.sh --dev

# 之后切换分支时，submodules 自动跟随
git checkout main       # → submodules 切到 main
git checkout main-dev   # → submodules 切到 main-dev
```

### 当前 Submodules

- `docs-public/` - 文档
- `packages/.../sage_db/sageDB/` - 数据库
- `packages/.../sage_flow/sageFlow/` - 工作流
- `packages/.../sage_vllm/sageLLM/` - LLM 服务

**重要**: `sage_db` 和 `sage_flow` 本身不是 submodules，实际 submodules 在其子目录中。

## 🔧 使用示例

### 场景 1：首次克隆并初始化

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 切换到开发分支
git checkout main-dev

# 一键初始化（会自动切换到 main-dev 分支）
./tools/maintenance/sage-maintenance.sh submodule init

# 验证所有 submodules 都在 main-dev 分支上
./tools/maintenance/sage-maintenance.sh submodule status
```

**预期输出：**
```
📦 Submodule 状态

🚀 SAGE Submodule 状态
SAGE 分支: main-dev

Submodule 配置：
Submodule                                          配置分支    当前分支   
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docs-public                                        main-dev    main-dev    (绿色 ✅)
sageLLM                                            main-dev    main-dev    (绿色 ✅)
sageDB                                             main-dev    main-dev    (绿色 ✅)
sageFlow                                           main-dev    main-dev    (绿色 ✅)
```

### 场景 2：切换 SAGE 分支

```bash
# 切换到 main 分支
git checkout main

# 自动切换所有 submodules 到 main 分支
./tools/maintenance/sage-maintenance.sh submodule switch

# 验证
./tools/maintenance/sage-maintenance.sh submodule status
```

### 场景 3：修复 detached HEAD 问题

如果你的 submodules 处于 detached HEAD 状态：

```bash
# 切换到正确的分支
./tools/maintenance/sage-maintenance.sh submodule switch

# 或者重新初始化
./tools/maintenance/sage-maintenance.sh submodule init
```

### 场景 4：定期更新

```bash
# 更新 SAGE 主仓库
git pull

# 更新所有 submodules
./tools/maintenance/sage-maintenance.sh submodule update

# 检查健康状态
./tools/maintenance/sage-maintenance.sh doctor
```

## 🆘 常见问题

### Detached HEAD 问题

**问题：** Submodule 初始化后停留在特定 commit 而非分支

**解决：**
```bash
./tools/maintenance/sage-maintenance.sh submodule switch
```

### Submodule 冲突

**问题：** Git merge 时 submodule 冲突

**解决：**
```bash
./tools/maintenance/sage-maintenance.sh submodule fix-conflict
```

### 旧配置清理

**问题：** Submodule 路径或配置变更

**解决：**
```bash
./tools/maintenance/sage-maintenance.sh submodule cleanup
git submodule sync
./tools/maintenance/sage-maintenance.sh submodule init
```

### Git Hooks 不工作

**解决：**
```bash
./tools/maintenance/sage-maintenance.sh setup-hooks -f
```

## 📝 最近更新

### 2025-10-09

✅ **修复了关键问题：**
1. 颜色显示修复 - 帮助信息现在正确显示颜色
2. Submodule 初始化修复 - `submodule init` 现在自动切换到正确的分支

详见 [CHANGELOG.md](./CHANGELOG.md)

## 📚 相关文档

- **开发指南** - [DEVELOPER.md](../../DEVELOPER.md)
- **贡献指南** - [CONTRIBUTING.md](../../CONTRIBUTING.md)
- **Submodule 详细指南** - [SUBMODULE_GUIDE.md](./SUBMODULE_GUIDE.md)
- **更新日志** - [CHANGELOG.md](./CHANGELOG.md)

---

💡 **提示：** 遇到问题先运行 `doctor`，它会给出诊断和建议！

## ⚠️ 注意事项

1. **优先使用主脚本** `sage-maintenance.sh`，不要直接调用 helpers 中的脚本
2. **Submodule 初始化** - 使用 `submodule init` 而不是 `git submodule update --init`
3. **分支切换后** - 运行 `submodule switch` 同步 submodules
4. **定期清理** - 使用 `clean` 命令保持环境整洁
5. **健康检查** - 定期运行 `doctor` 检查项目状态

## 📝 最新更新 (2025-10-09)

### 🐛 已修复的问题

1. **颜色显示问题** ✅
   - 修复了帮助信息显示 ANSI 转义代码的问题
   - 现在所有颜色和格式都能正确显示

2. **Submodule 初始化问题** ✅
   - 修复了 `submodule init` 导致 detached HEAD 的问题
   - 现在会自动切换到正确的分支（main 或 main-dev）

### 🎯 关键改进

- `submodule init` 现在是一键初始化 + 自动分支切换
- 新增颜色状态指示，更直观地查看 submodule 状态
- 改进了错误提示和使用说明

## 📚 更多帮助

### 查看帮助信息

```bash
# 查看完整帮助
./tools/maintenance/sage-maintenance.sh --help

# 健康检查（会给出详细建议）
./tools/maintenance/sage-maintenance.sh doctor

# 查看 submodule 详细状态
./tools/maintenance/sage-maintenance.sh submodule status
```

### 相关文档

- [Submodule 初始化指南](./SUBMODULE_GUIDE.md) - 详细的使用教程
- [更新日志](./CHANGELOG.md) - 最新的功能更新和修复
- [开发者文档](../../docs/dev-notes/) - 开发相关文档

### 获取支持

遇到问题？

1. � 运行健康检查：`./tools/maintenance/sage-maintenance.sh doctor`
2. 📋 查看状态：`./tools/maintenance/sage-maintenance.sh submodule status`
3. 📖 查阅文档：`./tools/maintenance/README.md`（本文件）
4. 🐛 提交 Issue：[GitHub Issues](https://github.com/intellistream/SAGE/issues)

---

�💡 **快速提示：** 遇到问题先运行 `doctor`，它会告诉你该怎么做！

🎨 **新功能：** 所有命令现在都有彩色输出，更容易识别状态！
