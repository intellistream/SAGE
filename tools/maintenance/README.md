# SAGE Maintenance Tools

统一的项目维护工具集，提供项目清理、安全检查、类型检查等功能。

> **注意：** 完整的开发指南请参见：
>
> - [DEVELOPER.md](../../DEVELOPER.md) - 开发环境设置
> - [CONTRIBUTING.md](../../CONTRIBUTING.md) - 贡献指南

> **⚠️ 重要变更：** SAGE 已不再使用 git submodules。所有依赖（如 SageVDB、NeuroMem 等）
> 现在都作为独立的 PyPI 包安装。`submodule` 相关命令已被移除。

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
# 清理项目构建产物
./tools/maintenance/sage-maintenance.sh clean

# 深度清理（包括 Python 缓存、日志等）
./tools/maintenance/sage-maintenance.sh clean-deep

# 检查配置文件中的敏感信息
./tools/maintenance/sage-maintenance.sh security-check

# 安装/重新安装 Git hooks
./tools/maintenance/sage-maintenance.sh setup-hooks
```

## 📋 命令参考

### 项目维护

| 命令             | 说明                 |
| ---------------- | -------------------- |
| `doctor`         | 运行完整健康检查     |
| `status`         | 显示项目状态         |
| `clean`          | 清理构建产物         |
| `clean-deep`     | 深度清理（包括缓存） |
| `security-check` | 检查敏感信息泄露     |
| `setup-hooks`    | 安装 Git hooks       |

### 类型检查工具

| 命令                                | 说明                     |
| ----------------------------------- | ------------------------ |
| `typecheck status`                  | 检查类型错误状态         |
| `typecheck show-new`                | 显示格式化后新增的错误   |
| `typecheck explain <file>`          | 解释文件修改原因         |
| `typecheck safe-commit`             | 安全提交（逐步提示）     |
| `typecheck reset`                   | 撤销自动格式化           |

## 📁 目录结构

```
tools/maintenance/
├── sage-maintenance.sh           # 主脚本（用户入口）
├── setup_hooks.sh               # Git hooks 安装
├── README.md                    # 本文档
├── CHANGELOG.md                 # 更新日志
├── git-hooks/                  # Hook 模板
└── helpers/                    # 内部辅助脚本
    ├── common.sh
    ├── quick_cleanup.sh
    └── check_config_security.sh
```

## 🔧 使用示例

### 项目清理

```bash
# 基础清理（构建产物、临时文件）
./tools/maintenance/sage-maintenance.sh clean

# 深度清理（包括 Python 缓存、日志等）
./tools/maintenance/sage-maintenance.sh clean-deep
```

### 健康检查

```bash
# 运行完整的健康检查
./tools/maintenance/sage-maintenance.sh doctor

# 查看项目状态
./tools/maintenance/sage-maintenance.sh status
```

### 安全检查

```bash
# 检查配置文件中的敏感信息
./tools/maintenance/sage-maintenance.sh security-check
```

### Git Hooks 管理

```bash
# 安装或重新安装 Git hooks
./tools/maintenance/sage-maintenance.sh setup-hooks
```

## 🆘 常见问题

### 如何清理项目？

**问题**: 构建产物、缓存占用空间过大

**解决**:

```bash
# 基础清理
./tools/maintenance/sage-maintenance.sh clean

# 深度清理（包括 Python 缓存、日志）
./tools/maintenance/sage-maintenance.sh clean-deep
```

### Git Hooks 不工作

**解决**:

```bash
./tools/maintenance/sage-maintenance.sh setup-hooks
```

## 📚 相关文档

- **开发指南** - [DEVELOPER.md](../../DEVELOPER.md)
- **贡献指南** - [CONTRIBUTING.md](../../CONTRIBUTING.md)
- **更新日志** - [CHANGELOG.md](./CHANGELOG.md)

---

💡 **提示**: 遇到问题先运行 `doctor`，它会给出诊断和建议！
