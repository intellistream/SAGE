````markdown
# L6 CLI Dev Notes

该目录追踪 `packages/sage-cli` (L6) 与 `packages/sage-tools` 的命令行接口文档。

## 目录结构

| 文件 | 说明 |
|------|------|
| `COMMAND_CHEATSHEET.md` | sage-dev 命令速查表 - 所有命令的快速参考 |
| `COMMAND_REORGANIZATION_SUMMARY.md` | 命令重组总结 - 2025-11 重组后的命令结构 |
| `CLI_HELP_UPDATE.md` | CLI 帮助信息更新记录 |

## CLI 架构

SAGE 提供两个主要的命令行入口：

### 1. `sage` (由 sage-cli 包提供)

平台管理和应用层命令：

```
sage
├── version        📋 版本信息
├── cluster        🌐 集群管理
├── head           🎯 头节点管理
├── worker         🔧 工作节点管理
├── job            📋 作业管理
├── jobmanager     ⚡ 作业管理器服务
├── config         ⚙️ 配置管理
├── doctor         🔍 系统诊断
├── extensions     🧩 扩展管理
├── docs           📚 文档管理
├── llm            🤖 LLM 服务管理
├── chat           🧭 编程助手
├── embedding      🎯 Embedding 管理
├── inference      🔮 统一推理服务
├── pipeline       🧱 Pipeline Builder
└── studio         🎨 可视化工作台
```

**代码位置**: `packages/sage-cli/src/sage/cli/main.py`

### 2. `sage-dev` (由 sage-tools 包提供)

开发工具命令：

```
sage-dev
├── quality/      🔍 质量检查
├── project/      📊 项目管理
├── maintain/     🔧 维护工具
├── package/      📦 包管理
├── resource/     💾 资源管理
├── github/       🐙 GitHub 管理
├── examples/     🔬 Examples 测试
├── maintenance/  🛠️ Dev-notes & Ruff 维护
└── docs/         📚 文档管理
```

**代码位置**: `packages/sage-tools/src/sage/tools/cli/commands/dev/__init__.py`

## 快速参考

### 常用命令

```bash
# 质量检查
sage-dev quality check           # 运行所有质量检查
sage-dev quality format          # 代码格式化

# 项目测试
sage-dev project test --coverage # 带覆盖率的测试

# 维护工具
sage-dev maintain doctor         # 健康检查
sage-dev maintain submodule init # 初始化子模块

# LLM 服务
sage llm serve                   # 启动 LLM 服务
sage studio start                # 启动 Studio
```

### 向后兼容

旧命令仍可使用但会显示弃用警告：

| 旧命令 | 新命令 |
|--------|--------|
| `sage-dev test` | `sage-dev project test` |
| `sage-dev check-all` | `sage-dev quality check` |
| `sage-dev status` | `sage-dev project status` |

## 相关文档

- [COMMAND_CHEATSHEET.md](./COMMAND_CHEATSHEET.md) - 完整命令速查
- [sage-tools README](../../../packages/sage-tools/README.md) - sage-tools 包文档
- [sage-cli 源码](../../../packages/sage-cli/src/sage/cli/) - CLI 实现

## 更新指引

当新增或修改 CLI 命令时：

1. 更新 `COMMAND_CHEATSHEET.md` 中的命令表格
2. 如有帮助文本变更，更新 `CLI_HELP_UPDATE.md`
3. 验证命令与代码实现一致
````
