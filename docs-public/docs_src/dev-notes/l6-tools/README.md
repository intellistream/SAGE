````markdown
# L6 Tools Dev Notes

该目录追踪 `packages/sage-tools` (L6) 和 `tools/` 目录的开发工具文档。

## 目录结构

| 文件 | 说明 | 状态 |
|------|------|------|
| `TOOLS_MIGRATION_NOTES.md` | tools → sage-tools 迁移记录 | ✅ 有效 |
| `INSTALLATION_TOOLS_ARCHITECTURE.md` | 安装工具架构决策 | ✅ 有效 |
| `SCRIPTS_CLEANUP_COMPLETE.md` | tools/scripts 清理完成记录 | ✅ 有效 |
| `PRE_COMMIT_AUTOFIX_GUIDE.md` | Pre-commit 自动修复指南 | ✅ 有效 |
| `SUBMODULE_OPERATIONS_GUIDE.md` | Submodule 运维与 CI 对齐指南 | ✅ 有效 |
| `CI_TEST_IMPROVEMENTS.md` | CI 测试与覆盖率强化 | ✅ 有效 |
| `CACHE_MANAGEMENT.md` | 缓存管理配置 | ✅ 有效 |
| `GIT_HOOKS_MIGRATION.md` | Git Hooks 迁移到 sage-tools | ✅ 有效 |
| `LOGGING_ENHANCEMENT.md` | 安装日志系统增强 | ✅ 有效 |
| `SELF_HOSTED_RUNNER_SETUP.md` | GitHub Actions Self-hosted Runner 配置 | ✅ 有效 |

## 架构概述

### 工具分类原则

| 类型 | 位置 | 说明 |
|------|------|------|
| **系统级安装脚本** | `tools/install/`, `tools/conda/` | 必须在安装 SAGE 前使用，保留 Shell |
| **Git/Shell 工具链** | `tools/git-tools/`, `tools/lib/` | 操作 Git、系统依赖，保留 Shell |
| **开发 CLI** | `packages/sage-tools/` | 需要 SAGE 依赖，迁移到 Python/Typer |
| **兼容入口** | `tools/dev.sh`, `tools/maintenance/` | 旧脚本入口，内部调用 sage-dev |

### sage-dev 命令组

详细命令参考见 [l6-cli/COMMAND_CHEATSHEET.md](../l6-cli/COMMAND_CHEATSHEET.md)

```
sage-dev
├── quality/       质量检查
├── project/       项目管理
├── maintain/      维护工具 (doctor, hooks, submodule)
├── package/       包管理 (pypi, version)
├── resource/      资源管理 (models)
├── github/        GitHub 管理
├── examples/      Examples 测试
├── maintenance/   Dev-notes & Ruff 维护
└── docs/          文档管理
```

## 快速参考

### 开发工作流

```bash
# 质量检查
sage-dev quality check           # 全部检查
sage-dev quality format          # 代码格式化

# 项目测试
sage-dev project test --coverage # 带覆盖率测试

# 维护
sage-dev maintain doctor         # 健康检查
sage-dev maintain submodule init # 初始化子模块
sage-dev maintain hooks install  # 安装 Git hooks
```

### 缓存管理

所有工具缓存统一到 `.sage/cache/`:
- `.sage/cache/mypy/` - Mypy 类型检查缓存
- `.sage/cache/ruff/` - Ruff 代码检查缓存
- `.sage/cache/pytest/` - Pytest 测试缓存

```bash
sage-dev project clean --deep    # 清理所有缓存
```

## 相关文档

- [sage-tools README](../../../../packages/sage-tools/README.md) - sage-tools 包文档
- [l6-cli/](../l6-cli/) - CLI 命令文档
- [tools/](../../../../tools/) - Shell 脚本工具
````
