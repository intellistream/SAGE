# SAGE Issues管理工具 - sage-tools集成版本

## 🎯 概述

SAGE Issues管理工具已成功迁移到 `sage-tools` 包中，并集成到 `sage dev` 命令组。这个工具提供了完整的GitHub Issues管理功能。

## 🚀 快速开始

### 基本命令结构

```bash
sage dev issues <command> [options]
```

### 🔍 查看状态

```bash
# 查看整体状态
sage dev issues status

# 查看配置信息
sage dev issues config
```

### 📥 下载Issues

```bash
# 下载所有Issues (开放 + 关闭)
sage dev issues download

# 只下载开放的Issues
sage dev issues download --state open

# 只下载已关闭的Issues
sage dev issues download --state closed

# 强制重新下载
sage dev issues download --force
```

### 📊 统计分析

```bash
# 显示Issues统计信息
sage dev issues stats
```

### 👥 团队管理

```bash
# 显示团队分析
sage dev issues team

# 更新团队信息
sage dev issues team --update

# 同时更新和分析
sage dev issues team --update --analysis
```

### 📋 项目管理

```bash
# 检测和修复错误分配的Issues
sage dev issues project

# 创建新Issue
sage dev issues create
```

## 📁 文件结构

迁移后的文件结构：

```
packages/sage-tools/src/sage/tools/dev/issues/
├── __init__.py          # 主模块入口
├── config.py            # 配置管理
├── manager.py           # 核心管理器
├── cli.py              # CLI命令接口
└── helpers/            # 辅助工具
    ├── __init__.py
    └── download_issues.py  # Issues下载器
```

## 🔧 配置

### GitHub Token设置

```bash
# 方法1: 环境变量
export GITHUB_TOKEN=your_github_token

# 方法2: 配置文件 (推荐)
echo "your_github_token" > ~/.github_token
```

### 数据存储位置

- 工作目录: `$SAGE_ROOT/output/issues-workspace/`
- 输出目录: `$SAGE_ROOT/output/issues-output/`
- 元数据目录: `$SAGE_ROOT/output/issues-metadata/`

## 🔄 迁移说明

### 原有工具位置

- **原位置**: `~/SAGE/tools/issues-management/`
- **新位置**: `~/SAGE/packages/sage-tools/src/sage/tools/dev/issues/`

### 命令对比

| 原命令                                                   | 新命令                     |
| -------------------------------------------------------- | -------------------------- |
| `./issues_manager.sh`                                    | `sage dev issues status`   |
| `python3 _scripts/download_issues.py`                    | `sage dev issues download` |
| `python3 _scripts/issues_manager.py --action statistics` | `sage dev issues stats`    |
| `python3 _scripts/issues_manager.py --action team`       | `sage dev issues team`     |

### 兼容性

- ✅ 保持相同的数据格式和存储结构
- ✅ 保持相同的配置文件和设置
- ✅ 保持相同的GitHub API集成
- ✅ 改进了用户界面和命令结构

## 🎨 新特性

1. **统一的CLI界面**: 集成到 `sage dev` 命令组
1. **改进的用户体验**: 使用Rich库提供美观的输出
1. **更好的错误处理**: 清晰的错误信息和建议
1. **模块化设计**: 更容易扩展和维护

## 🔮 下一步

以下功能将在后续版本中添加：

- [ ] AI分析和整理功能
- [ ] 同步功能 (上传到GitHub)
- [ ] 更多辅助工具的迁移
- [ ] 高级过滤和搜索功能

## 🐛 问题报告

如果遇到问题，请：

1. 检查GitHub Token是否正确配置
1. 运行 `sage dev issues status` 查看状态
1. 查看详细的错误信息
1. 在SAGE项目中创建Issue报告

______________________________________________________________________

*此文档更新于 2025-09-13*
