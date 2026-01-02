# tools → sage-tools 迁移笔记（合并版）

**Date**: 2025-11-25 \
**Author**: SAGE Development Team \
**Summary**: 统一记录 `tools/` 目录的角色划分、已完成的迁移、后续计划与清理结果，取代原有的分析 / 清理 / 进度三份文档。

______________________________________________________________________

## 1. 角色划分（Architecture Decision）

| 类型                       | 典型路径                                                   | 处理策略                   | 原因                                                               |
| -------------------------- | ---------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------ |
| **系统级安装脚本**         | `tools/install/`, `tools/conda/`                           | 保留 Shell（不迁移）       | 必须在安装 SAGE 之前即可使用；依赖 apt/conda、无 Python 环境也能跑 |
| **Git / Shell 工具链**     | `tools/git-tools/`, `tools/lib/`, `tools/maintenance/*.sh` | 保留                       | 操作 Git、系统依赖或调用其他 shell 函数；迁移成本高且无收益        |
| **开发 CLI / Python 脚本** | `tools/maintenance/helpers/*.py`, `tools/tests/*.py`       | 迁入 `packages/sage-tools` | 需要 SAGE 依赖、便于复用 Rich Typer CLI、统一发版                  |
| **兼容入口**               | `tools/dev.sh`, `tools/maintenance/sage-maintenance.sh`    | 保留但提示迁移             | 作为旧脚本入口，内部改为调用 `sage-dev` 命令，逐步引导用户         |

______________________________________________________________________

## 2. 已完成的迁移

| #   | 原文件                           | 新位置 / CLI                                                                               | 说明                                        |
| --- | -------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------- |
| 1   | `tools/tests/`                   | `packages/sage-tools/tests/`                                                               | 所有 Examples 测试迁移，原目录仅保留 README |
| 2   | `devnotes_organizer.py`          | `sage.tools.dev.maintenance.devnotes_organizer` → `sage-dev maintenance organize-devnotes` | 迁移 Python 脚本 + Typer CLI                |
| 3   | `batch_fix_devnotes_metadata.py` | `sage.tools.dev.maintenance.metadata_fixer` → `sage-dev maintenance fix-metadata`          | 统一入口                                    |
| 4   | `update_ruff_ignore.py`          | `sage.tools.dev.maintenance.ruff_updater` → `sage-dev maintenance update-ruff-ignore`      | 维护命令新增 `list` 输出现状                |
| 5   | \`tools/dev.sh docs              | serve-docs                                                                                 | clean\`                                     |
| 6   | `tools/git-hooks/install.sh`     | `sage.tools.dev.hooks` + `sage-dev maintain hooks <cmd>`                                   | Git hooks Python 化并集成 Typer UI          |

新命令总览：

```
sage-dev
├── examples analyze|test|check|info
├── maintenance organize-devnotes|fix-metadata|update-ruff-ignore|list
├── docs build|serve|check|list
├── maintain hooks install|uninstall|status|reinstall
└── project clean/test ...
```

______________________________________________________________________

## 3. 清理结果

- `tools/tests/` 目录下的 Python 代码全部删除，只保留迁移说明。
- `packages/sage-tools/examples/` 移动到 `packages/sage-tools/tests/examples/`，与 pytest 结构保持一致。
- `packages/sage-tools/CLEANUP_COMPLETE.md`, `PHASE2_COMPLETE.md`,
  `MAINTENANCE_MIGRATION_COMPLETE.md` 用于追踪不同阶段的完成情况。
- 旧脚本在执行时会输出类似提示：
  ```bash
  ⚠️  此命令已迁移到 sage-dev docs build
  ```
  然后继续调用新命令，保证兼容性。

______________________________________________________________________

## 4. 进度 & 下一步

| 阶段    | 状态      | 内容                                                                      |
| ------- | --------- | ------------------------------------------------------------------------- |
| Phase 1 | ✅ 完成   | 迁移 tests + maintenance helpers + docs CLI；保证向后兼容                 |
| Phase 2 | ⏳ 进行中 | 为新增 CLI 增补单元测试、错误提示和进度条                                 |
| Phase 3 | 📝 规划中 | 逐步把 `tools/dev.sh` 余下命令映射到 `sage-dev`，例如 `setup`, `validate` |
| Phase 4 | 🔮 长期   | 统计旧脚本的使用情况，确认可安全删除时再移除                              |

______________________________________________________________________

## 5. 推荐实践

1. **优先使用 `sage-dev`**：CI、文档、维护脚本都应切换到 `sage-dev` 命令，获取统一的日志和返回码。
1. **Shell 脚本作为入口**：`tools/dev.sh` / `sage-maintenance.sh` 可继续使用，但建议仅作为 wrapper。
1. **DAG 化的维护命令**：`sage-dev maintain submodule <cmd>`、`sage-dev maintain hooks <cmd>` 将逐渐替换
   `tools/maintenance/*.sh`。
1. **贡献新工具**：如需要新增 CLI 功能，请直接放到 `packages/sage-tools` 并挂载到合适的命令组，再考虑是否需要 Shell wrapper。

______________________________________________________________________

## 6. TODO / Ideas

- [ ] `sage-dev maintain submodule` 暴露更多 `manage.sh` 能力（status、switch、bootstrap）。
- [ ] 为 `examples` CLI 添加并行执行与失败快照。
- [ ] 在 `sage-dev docs build` 中加入增量构建 / 缓存。
- [ ] 监控 `tools/dev.sh` 的调用频率，准备废弃计划。

______________________________________________________________________

**结论**：`tools/` 继续聚焦“安装 + Shell 管理”，而开发工具、检查器、辅助脚本都应通过 `sage-dev` CLI 暴露到
`packages/sage-tools`。本文档作为唯一的迁移记录与路线图，替代旧的分析 / 清理 / 进度三篇文档。
