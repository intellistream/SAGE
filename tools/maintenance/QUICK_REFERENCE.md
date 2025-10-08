# SAGE 维护工具快速参考

## 🚀 一键命令

```bash
# 最常用的命令
./tools/maintenance/sage-maintenance.sh doctor    # 健康检查
./tools/maintenance/sage-maintenance.sh status    # 查看状态
./tools/maintenance/sage-maintenance.sh clean     # 清理项目
```

## 📦 Submodule 管理

| 命令 | 说明 |
|------|------|
| `submodule status` | 查看 submodule 状态 |
| `submodule switch` | 切换分支（main → main, 其他 → main-dev） |
| `submodule init` | 初始化所有 submodules |
| `submodule update` | 更新所有 submodules |
| `submodule fix-conflict` | 解决冲突 |
| `submodule cleanup` | 清理旧配置 |

## 🧹 清理命令

| 命令 | 说明 |
|------|------|
| `clean` | 标准清理（构建产物、缓存） |
| `clean-deep` | 深度清理（+ Python 缓存、日志） |

## 🔧 其他工具

| 命令 | 说明 |
|------|------|
| `security-check` | 检查 API key 泄露 |
| `setup-hooks` | 安装 Git hooks |
| `doctor` | 完整健康检查 |
| `status` | 项目状态概览 |

## 🆘 常见问题速查

### Submodule 错误
```bash
# "refusing to create/use in another submodule's git dir"
./tools/maintenance/sage-maintenance.sh submodule cleanup
```

### Git hooks 未工作
```bash
./tools/maintenance/sage-maintenance.sh setup-hooks -f
```

### 构建问题
```bash
./tools/maintenance/sage-maintenance.sh clean-deep
```

## 💡 选项

| 选项 | 说明 |
|------|------|
| `-h, --help` | 显示帮助 |
| `-v, --verbose` | 详细输出 |
| `-f, --force` | 跳过确认 |

## 📍 当前 Submodule 路径

```
packages/sage-middleware/src/sage/middleware/components/
├── sage_db/sageDB/      ← Submodule
├── sage_flow/sageFlow/  ← Submodule
└── sage_vllm/sageLLM/   ← Submodule
docs-public/             ← Submodule
```

**注意**: `sage_db` 和 `sage_flow` 本身**不是** submodules！

---
💡 遇到问题先运行 `doctor`，它会告诉你该怎么做！
