````markdown
# L6 CLI Dev Notes

该目录追踪 `packages/sage-cli` (L6) 与 `packages/sage-tools` 的命令行接口文档。

## 目录结构

| 文件 | 说明 |
|------|------|
| `COMMAND_CHEATSHEET.md` | `sage`/`sage-dev` 命令速查表（完整命令结构与示例） |
| `COMMAND_REORGANIZATION_SUMMARY.md` | `sage-dev` 命令重组总结（旧 → 新 映射与兼容策略） |
| `CLI_HELP_UPDATE.md` | `sage` / `sage-dev` 帮助信息与 UX 更新记录 |
| `llm-preset-launcher.md` | LLM 预设启动器设计（Control Plane 预设引擎管理） |

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

## 命令结构与重组概览

`sage-dev` 在 2025-11 完成了一次较大规模的命令重组，核心目标是将原先扁平的 15+ 顶层命令，收敛为少量语义清晰的命令组：

- 顶层结构：`sage-dev <group> <command>`，最多 4 级（如 `sage-dev maintain submodule init`）。
- 九大命令组：`quality`、`project`、`maintain`、`package`、`resource`、`github`、`examples`、`maintenance`、`docs`，职责边界清晰。
- 旧命令（如 `sage-dev test`、`sage-dev check-all` 等）在 `dev/main.py` 中保留包装，并在执行时输出弃用提示，引导用户迁移到新路径（如 `sage-dev project test`、`sage-dev quality check`）。

> 具体的组内命令列表与“旧 → 新”映射表见 `COMMAND_CHEATSHEET.md` 与 `COMMAND_REORGANIZATION_SUMMARY.md`，实现位置集中在 `packages/sage-tools/src/sage/tools/cli/commands/dev/` 目录下。

## 帮助信息与 UX 更新

为提升命令可发现性，`sage` 与 `sage-dev` 的 `--help` 输出在 2025-10 完成了一轮对齐与增强：

- `sage --help`：按 Platform / Apps 两大类分组展示命令，并在帮助说明中显式提示“开发相关任务请使用 `sage-dev`”。
- `sage-dev` 顶层：增加欢迎回调，直接展示常用命令示例（quality / project / maintain / package）与所有命令组的简要说明。
- 各子命令组（如 `quality`、`project`、`maintain`、`docs` 等）均补全了组级 help 文本和子命令摘要，使 `sage-dev <group> --help` 成为自解释的接口文档。

这些更新的设计与截图记录在 `CLI_HELP_UPDATE.md` 中，实际实现分别位于 `sage/cli/main.py` 与 `sage/tools/cli/commands/dev/__init__.py` 中的 Typer 应用定义。

## LLM 预设启动器设计概要

为方便一次性启动“一组 LLM + Embedding 引擎”，CLI 侧设计了 `sage llm preset` 命令族，与 Control Plane 的 `EngineStartRequest` / `/v1/management/engines` 接口联动：

- **Presets 描述**：使用简单的 YAML 文件（存放在 `sage.llm/presets/`），声明多个引擎及其元数据（`kind=llm|embedding`、模型、并行度、端口、标签、metadata 等）。
- **Engine Kind 语义**：通过 `engine_kind` 区分 `llm` 与 `embedding` 运行时，使 Control Plane 能在调度时区分 GPU 需求与请求类型。
- **CLI 工作流**：
	- `sage llm preset list|show`：列出内置预设并查看具体 YAML。
	- `sage llm preset apply <name|--file>`：解析 preset，并为每个引擎依次调用 `/v1/management/engines`，支持 `--dry-run`。
- **失败与回滚策略**：当某个引擎启动失败时，默认尝试回滚已成功的引擎，除非用户显式指定 `--no-rollback`。

完整设计细节与字段说明见 `llm-preset-launcher.md`；L1 层的 Control Plane 增强（如 `engine_kind` 扩展与注册表更新）在 `l1-common` dev-notes 中有对应总结。

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
- [sage-tools README](../../../../packages/sage-tools/README.md) - sage-tools 包文档
- [sage-cli 源码](../../../../packages/sage-cli/src/sage/cli/) - CLI 实现

## 更新指引

当新增或修改 CLI 命令时：

1. 更新 `COMMAND_CHEATSHEET.md` 中的命令表格
2. 如有帮助文本变更，更新 `CLI_HELP_UPDATE.md`
3. 验证命令与代码实现一致
````
