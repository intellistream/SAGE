# SAGE Scripts

此目录包含 SAGE 项目的辅助脚本和命令行工具。

## 📂 脚本列表

### 🔧 开发工具

| 脚本 | 说明 |
|------|------|
| `dev.sh` | 开发环境辅助脚本 |
| `sage-jobmanager.sh` | Job Manager CLI 包装器 |

### 📚 工具库

| 脚本 | 说明 |
|------|------|
| `common_utils.sh` | 通用工具函数（引用自 tools/lib） |
| `logging.sh` | 日志工具（引用自 tools/lib） |

## 🚀 使用方式

### Job Manager

`sage-jobmanager.sh` 是一个包装器脚本，确保在正确的 conda 环境中执行 jobmanager 命令：

```bash
# 直接使用（会自动检测或使用当前 conda 环境）
./scripts/sage-jobmanager.sh <command> [args]

# 或者先激活环境
conda activate sage
./scripts/sage-jobmanager.sh <command> [args]
```

## 📝 注意事项

- 这些脚本主要用于项目内部使用
- 如需维护脚本，请查看 `tools/maintenance/`
- 通用函数库实际位于 `tools/lib/`

## 🔗 相关目录

- **维护工具**: `tools/maintenance/` - 项目维护和诊断工具
- **工具库**: `tools/lib/` - 共享函数库
- **安装工具**: `tools/install/` - 安装和配置脚本
