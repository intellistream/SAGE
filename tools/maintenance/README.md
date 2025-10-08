# SAGE Maintenance Tools

统一的项目维护工具集。

## 🚀 快速开始

```bash
# 健康检查（推荐首先运行）
./tools/maintenance/sage-maintenance.sh doctor

# 查看所有命令
./tools/maintenance/sage-maintenance.sh --help
```

## 📋 常用命令

| 命令 | 说明 |
|------|------|
| `doctor` | 运行完整健康检查 |
| `status` | 显示项目状态 |
| `submodule status` | 查看 submodule 状态 |
| `submodule switch` | 切换 submodule 分支 |
| `submodule cleanup` | 清理旧 submodule 配置 |
| `clean` | 清理构建产物 |
| `clean-deep` | 深度清理（包括缓存） |
| `security-check` | 检查敏感信息泄露 |
| `setup-hooks` | 安装 Git hooks |

## 📁 目录结构

```
tools/maintenance/
├── sage-maintenance.sh      # 主脚本（用户入口）
├── setup_hooks.sh           # Git hooks 安装
├── git-hooks/              # Hook 模板
└── helpers/                # 内部脚本
```

## 📦 Submodule 自动管理

### 分支策略

| SAGE 分支 | Submodules 分支 |
|-----------|----------------|
| `main` | `main` |
| 其他任何分支 | `main-dev` |

### 自动化设置

```bash
# 安装 SAGE（开发模式）
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

## 🆘 常见问题

### Submodule 冲突错误

```bash
# 错误: "refusing to create/use in another submodule's git dir"
./tools/maintenance/sage-maintenance.sh submodule cleanup
git submodule sync
git submodule update --init --recursive
```

### Git hooks 不工作

```bash
./tools/maintenance/sage-maintenance.sh setup-hooks -f
```

### 项目状态异常

```bash
./tools/maintenance/sage-maintenance.sh doctor
# 按提示运行建议的命令
```

## ⚠️ 注意事项

1. **优先使用主脚本** `sage-maintenance.sh`，不要直接调用 helpers 中的脚本
2. **开发模式自动化** - Git hooks 会自动管理 submodules
3. **定期清理** - 使用 `clean` 命令保持环境整洁

## 📚 更多帮助

```bash
# 查看完整帮助
./tools/maintenance/sage-maintenance.sh --help

# 健康检查（会给出详细建议）
./tools/maintenance/sage-maintenance.sh doctor
```

---

💡 遇到问题先运行 `doctor`，它会告诉你该怎么做！
