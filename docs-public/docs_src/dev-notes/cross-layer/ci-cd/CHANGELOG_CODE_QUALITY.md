# 代码质量配置统一 - 变更总结

**Date**: 2024-10-29\
**Author**: SAGE Team\
**Summary**: 统一了整个项目的代码质量检查配置，解决了 CI/CD 和本地环境不一致的问题

## 📋 本次变更概述

统一了整个项目的代码质量检查配置，解决了 CI/CD 和本地环境不一致的问题。

## 🎯 解决的问题

1. **CI/CD 失败但本地没有检查** - Pre-commit hooks 未触发
1. **代码格式反复修改** - isort 和 ruff 配置冲突
1. **配置分散难以维护** - 每个包有独立配置

## ✅ 主要变更

### 1. 统一配置架构

**新增文件**：

- `tools/ruff.toml` - 根级统一代码质量配置
- `tools/pytest.ini` - 根级测试配置
- `tools/fix-code-quality.sh` - 代码质量自动修复脚本
- `tools/verify-precommit.sh` - Pre-commit 验证脚本
- `docs/dev-notes/ci-cd/code-quality-guide.md` - 完整配置指南

**修改文件**：

- `tools/pre-commit-config.yaml` - 移除 isort，更新 ruff hooks
- `packages/*/pyproject.toml` (所有11个包) - 移除独立配置，继承根配置

### 2. 配置继承机制

所有子包现在通过 `extend` 继承根配置：

```toml
# packages/*/pyproject.toml
[tool.ruff]
extend = "../../tools/ruff.toml"
```

### 3. Pre-commit Hooks 优化

**之前**：

```yaml
- black (格式化)
- isort (import 排序)  ← 移除
- ruff (lint)
```

**现在**：

```yaml
- black (格式化)
- ruff check (lint + import 排序)  ← 统一
- ruff format (备用格式化)
```

## 📊 影响范围

### 修改的文件统计

- 配置文件: 12 个 (11个子包 + 1个 pre-commit)
- 新增工具: 2 个脚本
- 新增配置: 2 个 (tools/ruff.toml, tools/pytest.ini)
- 文档: 1 个完整指南

### 代码修改

- **自动格式化**: ~300 个文件（black + ruff）
- **Import 排序**: ~100 个文件（ruff isort）
- **Lint 修复**: ~350 个自动修复

### 剩余问题

- 65 个 lint 错误需要手动修复（主要是代码质量问题，如 B008 等）

## 🔄 开发流程变化

### 之前

```bash
# 每个包可能有不同的配置
# isort 和 ruff 可能冲突
# 本地和 CI 不一致
```

### 现在

```bash
# 1. 初次设置
pre-commit install --config tools/pre-commit-config.yaml

# 2. 日常开发
git commit  # 自动运行检查

# 3. 提交前修复
./tools/fix-code-quality.sh

# 4. 验证配置
./tools/verify-precommit.sh
```

## 📝 待办事项

### 立即执行（本次提交）

- [x] 创建根级 ruff.toml
- [x] 创建根级 pytest.ini
- [x] 更新所有子包配置
- [x] 更新 pre-commit 配置
- [x] 创建工具脚本
- [x] 编写配置文档
- [x] 运行自动格式化
- [ ] 提交所有变更

### 后续优化

- [ ] 修复剩余 65 个 lint 错误
- [ ] 更新 CONTRIBUTING.md
- [ ] 团队培训和文档分享
- [ ] 考虑添加 ruff 到 CI/CD 的单独检查步骤

## 🎓 关键决策

### 为什么移除 isort？

1. **性能**: Ruff 比 isort 快 10-100 倍
1. **一致性**: 避免两个工具配置冲突
1. **简化**: 一个工具完成多个任务
1. **趋势**: Ruff 正在成为 Python 社区标准

### 为什么使用根级配置？

1. **一致性**: 所有包遵循相同标准
1. **维护性**: 单点配置，易于更新
1. **可扩展**: 子包可以根据需要覆盖特定规则
1. **标准化**: 符合 monorepo 最佳实践

## 📚 文档位置

- **主文档**: `docs/dev-notes/ci-cd/code-quality-guide.md`
- **故障排除**: `docs/dev-notes/ci-cd/pre-commit-troubleshooting.md`
- **配置文件**: `ruff.toml`, `pytest.ini`
- **工具脚本**: `tools/fix-code-quality.sh`, `tools/verify-precommit.sh`

## 🔗 相关 Issue/PR

- 解决 CI/CD 代码质量检查失败问题
- 统一项目代码风格标准
- 改善开发者体验

## ✅ 验证清单

- [x] 所有子包配置已更新
- [x] Pre-commit hooks 可以正常运行
- [x] 工具脚本测试通过
- [x] 文档完整准确
- [x] 不再出现反复格式化问题
- [x] "legacy alias" 警告已解决

## 📌 注意事项

1. **首次拉取后需要**:

   ```bash
   pre-commit install --config tools/pre-commit-config.yaml
   ```

1. **不要跳过 hooks**:

   - 避免使用 `git commit -n`
   - 让 pre-commit 正常运行

1. **编辑器配置**:

   - 推荐配置自动格式化
   - 参考 `code-quality-guide.md`

1. **剩余 lint 错误**:

   - 不影响提交
   - 可以逐步修复
   - 主要是代码质量建议
