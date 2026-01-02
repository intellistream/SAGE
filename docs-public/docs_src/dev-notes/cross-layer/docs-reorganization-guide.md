# 📚 文档整理指南

## 快速开始

我们已经更新了 pre-commit hooks 来检测散落的文档文件。发现了 **62 个**需要整理的文档。

### 🔍 检查当前违规

```bash
# 查看所有违规文件
PRE_COMMIT_FROM_REF=HEAD PRE_COMMIT_TO_REF=HEAD bash tools/hooks/check_docs_location.sh

# 查看详细审计报告
cat .sage/docs-location-violations-report.md
```

### 🚀 执行整理（推荐分阶段）

#### Phase 1: 包根目录违规（高优先级）⚡

```bash
# 演习模式 - 查看将要做什么
./tools/scripts/reorganize_scattered_docs.sh --phase 1 --dry-run

# 执行整理
./tools/scripts/reorganize_scattered_docs.sh --phase 1

# 提交更改
git add -A
git commit -m "docs: 移动包根目录违规文档到 docs/ 目录"
```

#### Phase 2: amms/ 散落文档（高优先级）⚡

```bash
# 演习模式
./tools/scripts/reorganize_scattered_docs.sh --phase 2 --dry-run

# 执行整理
./tools/scripts/reorganize_scattered_docs.sh --phase 2

# 提交更改
git add -A
git commit -m "docs(sage-libs): 整理 amms/ 散落文档"
```

#### Phase 3-5: 其他文档（可选）

```bash
# Phase 3: anns/ 文档
./tools/scripts/reorganize_scattered_docs.sh --phase 3

# Phase 4: benchmark 文档（建议手动审查）
# 查看 .sage/docs-location-violations-report.md

# Phase 5: tools/ 和其他
./tools/scripts/reorganize_scattered_docs.sh --phase 5
```

#### 一键整理所有（谨慎使用）

```bash
# 演习模式查看所有操作
./tools/scripts/reorganize_scattered_docs.sh --all --dry-run

# 执行所有阶段
./tools/scripts/reorganize_scattered_docs.sh --all
```

## 📋 统计信息

- **总扫描文件**: 272 个 MD 文件在 `packages/*/src/`
- **第三方库（已排除）**: 101 个（SPTAG, faiss, diskann-ms 等）
- **项目违规**: 62 个
  - 🔴 高优先级: 12 个（包根 + amms）
  - 🟡 中优先级: 32 个（anns + benchmark）
  - 🟢 低优先级: 18 个（tools + 其他）

## ✅ 文档位置规则

### 允许的位置

```
✅ packages/<package>/README.md           # 包主文档
✅ packages/<package>/CHANGELOG.md        # 变更日志
✅ packages/<package>/docs/               # 详细文档
✅ packages/<package>/src/.../submodule/docs/  # 子模块文档
✅ docs-public/docs_src/                  # 集中式文档
✅ examples/<name>/README.md              # 示例文档
✅ tools/<tool>/docs/                     # 工具文档
```

### 禁止的位置

```
❌ packages/<package>/*.md (除 README.md, CHANGELOG.md)
❌ packages/<package>/src/**/*.md (除 docs/ 子目录)
```

### 自动排除（第三方库）

```
🚫 packages/.*/implementations/SPTAG/
🚫 packages/.*/implementations/faiss/
🚫 packages/.*/implementations/diskann-ms/
🚫 packages/.*/implementations/pybind11/
🚫 其他第三方库...
```

## 🔧 Pre-commit Hook

Hook 已自动配置，会在 `git commit` 时检查：

```bash
# 手动运行检查
pre-commit run markdown-files-location-check --all-files

# 绕过检查（不推荐）
git commit --no-verify
```

## 📖 相关文档

- **审计报告**: `.sage/docs-location-violations-report.md`
- **更新总结**: `.sage/docs-enforcement-update-summary.md`
- **策略文档**: `docs-public/docs_src/dev-notes/cross-layer/documentation-policy.md`

## ⚠️ 注意事项

1. **演习模式**: 首次执行建议使用 `--dry-run` 查看操作
1. **内部链接**: 移动后需要更新引用文档的链接
1. **分阶段执行**: 推荐按阶段执行，便于审查和回滚
1. **备份**: 虽然使用 `git mv` 保留历史，但建议提前备份

## 🆘 常见问题

**Q: 我的 MD 文件被误报为违规？** A: 检查是否是第三方库文档，如果是，更新 `tools/hooks/check_docs_location.sh` 的
`third_party_patterns`

**Q: 子模块的文档怎么处理？** A: 子模块内的 MD 必须放在 `submodule/docs/` 子目录

**Q: 我需要跳过某些文件？** A: 更新 `tools/hooks/check_docs_location.sh` 的 `allowed_patterns`

**Q: 如何回滚？** A: 使用 `git revert` 或 `git reset` 恢复提交

## 🎯 推荐执行顺序

1. ✅ 阅读本指南
1. ✅ 查看审计报告 (`.sage/docs-location-violations-report.md`)
1. ⚡ 执行 Phase 1（包根目录，4 个文件）
1. ⚡ 执行 Phase 2（amms 文档，8 个文件）
1. 📋 提交 Phase 1+2 的更改
1. �� 审查 Phase 3-5 是否需要执行
1. ✅ 运行 pre-commit 检查验证
1. ✅ 更新内部链接（如需要）

______________________________________________________________________

**维护者**: IntelliStream Team\
**更新时间**: 2026-01-02
