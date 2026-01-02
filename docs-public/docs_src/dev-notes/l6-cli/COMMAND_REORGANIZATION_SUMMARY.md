**Date**: 2025-11-25\
**Author**: SAGE Development Team\
**Summary**: sage-dev 命令重组完成总结——记录新的 9 个命令组、代码位置以及遗留兼容策略。

______________________________________________________________________

# sage-dev 命令重组总结

## 📌 背景

- 旧版 `sage-dev` 一共有 15 个顶层命令（quality / status / analyze / test / clean / pypi / version / models /
  issues ...），可发现性和扩展性较差。
- 目标：按功能重新分组，提供统一的 `sage-dev <group> <command>` 语义；同时保留旧命令以兼容现有脚本。
- 代码位置：
  - `sage` 平台 / 应用命令 → `packages/sage-cli/src/sage/cli/main.py`
  - `sage-dev` 开发命令 → `packages/sage-tools/src/sage/tools/cli/commands/dev/__init__.py`
  - 旧命令实现仍保留在 `.../dev/main.py`，被新的分组命令复用。

## 🧱 最终命令结构

```
sage-dev
├── quality/      🔍 质量检查（check, architecture, devnotes, readme, fix）
├── project/      📊 项目管理（status, analyze, clean, test, architecture, home）
├── maintain/     🔧 维护工具（doctor, hooks, security, submodule/*, clean）
├── package/      📦 包管理（install, pypi/*, version/*）
├── resource/     💾 资源管理（models configure/cache/check/clear）
├── github/       🐙 GitHub 管理（issues 子命令）
├── examples/     🔬 Examples 测试工具（analyze, test, check, info）
├── maintenance/  🛠️ 文档与 Ruff 维护（organize-devnotes, fix-metadata, update-ruff-ignore, list）
└── docs/         📚 文档管理（build, serve, check, list）
```

| 组名        | 模块路径                                                                  | 职责 / 备注                                                                       |
| ----------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| quality     | `packages/sage-tools/src/sage/tools/cli/commands/dev/quality/__init__.py` | 调用 legacy `main.py` 中的 quality/check-\* 函数，提供架构、文档、README 检查入口 |
| project     | `.../project/__init__.py`                                                 | 包含 status/analyze/test/clean/home 等项目生命周期命令                            |
| maintain    | `.../maintain/__init__.py`                                                | 包装 `tools/maintenance/sage-maintenance.sh` 能力，含 submodule 子命令            |
| package     | `.../package/__init__.py`                                                 | 聚合 PyPI、版本、安装命令；子模块引用 `package_version.py` 等实现                 |
| resource    | `.../resource/__init__.py`                                                | 暴露模型缓存相关命令（configure/cache/check/clear）                               |
| github      | `.../github/__init__.py`                                                  | 目前仅注册 `issues` Typer app（功能迁移仍在进行中）                               |
| examples    | `.../examples.py`                                                         | 新增的 Examples 测试命令，需要开发环境                                            |
| maintenance | `.../maintenance.py`                                                      | Dev-notes 整理、元数据修复、Ruff ignore 批量更新                                  |
| docs        | `.../docs.py`                                                             | 构建 / 预览 / 检查 `docs-public`，并提供命令列表                                  |

## 🔄 旧 → 新 命令映射

| 旧命令                                                            | 新命令路径                               | 状态                              |
| ----------------------------------------------------------------- | ---------------------------------------- | --------------------------------- |
| `check-all`                                                       | `sage-dev quality check`                 | 直接调用 quality 组，行为保持一致 |
| `check-architecture`                                              | `sage-dev quality architecture`          | 新组提供细粒度参数                |
| `check-devnotes`                                                  | `sage-dev quality devnotes`              | 延续原逻辑                        |
| `check-readme`                                                    | `sage-dev quality readme`                | README 检查拆进 quality 组        |
| `quality`（带 --format/--lint 等）                                | `sage-dev quality fix` / `quality check` | 根据是否修复拆成 fix / check      |
| `status` / `analyze` / `clean` / `test` / `architecture` / `home` | `sage-dev project <command>`             | 一致映射                          |
| `pypi <cmd>`                                                      | `sage-dev package pypi <cmd>`            | 与 PyPI CLI 保持一致              |
| `version <cmd>`                                                   | `sage-dev package version <cmd>`         | 版本管理挪到 package 组           |
| `models <cmd>`                                                    | `sage-dev resource models <cmd>`         | 模型缓存命令迁移完成              |
| `issues <cmd>`                                                    | `sage-dev github issues <cmd>`           | 仍旧注册在 github 组下            |
| `dev.sh` / `sage-maintenance.sh` 中的 submodule / doctor / hooks  | `sage-dev maintain ...`                  | 通过 Typer 包装脚本实现           |

> **提示**：`packages/sage-tools/src/sage/tools/cli/commands/dev/main.py` 中保留同名 Typer
> 命令以确保旧脚本仍可直接调用；新的分组命令通过 import 复用这些实现。

## ♻️ 兼容策略与提醒

1. **双入口共存**：
   - `sage` CLI（packages/sage-cli）负责平台 & 应用命令。
   - `sage-dev` CLI（packages/sage-tools）负责开发命令，并在欢迎信息中列出所有命令组。
1. **向后兼容**：
   - 旧命令仍在 `dev/main.py` 中注册；分组命令内部直接调用这些函数。
   - 通过 `typer.Exit`/Rich 输出给出 deprecation 提示（例如 `sage-dev check-all` 建议迁移到 `quality check`）。
1. **文档同步**：
   - `CLI_HELP_UPDATE.md` 记录了帮助信息更新。
   - `COMMAND_CHEATSHEET.md` 提供操作示例。
1. **待完成事项**：
   - `sage-dev github issues` 仍标记为“待完整迁移”。
   - legacy `dev/main.py` 可以在未来版本逐步精简，只保留必要包装。

## 📚 相关引用

- `packages/sage-cli/src/sage/cli/main.py` – 顶层 `sage` 命令入口。
- `packages/sage-tools/src/sage/tools/cli/commands/dev/__init__.py` – `sage-dev` Typer 应用注册处。
- `packages/sage-tools/src/sage/tools/cli/commands/dev/main.py` – 旧命令实现与兼容逻辑。
- [CLI_HELP_UPDATE.md](./CLI_HELP_UPDATE.md) – 帮助文本更新记录。
- [COMMAND_CHEATSHEET.md](./COMMAND_CHEATSHEET.md) – 重组后命令速查表。
