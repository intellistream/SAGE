______________________________________________________________________

## 标题: 本地 sage-dev quality fix 与 CI/CD 质量检查不一致问题 分类: 问题分析 状态: 已识别 创建日期: 2025-11-22 作者: GitHub Copilot 相关: l6-tools, ci-cd

# 本地 sage-dev quality fix 与 CI/CD 质量检查不一致问题

## 🐛 问题描述

**症状**: 本地运行 `sage-dev quality fix` 显示通过，但 CI/CD 构建失败

**影响**: 开发者无法在本地准确预测 CI/CD 的检查结果，导致不必要的 push-fix 循环

## 🔍 根本原因

### 本地 `sage-dev quality fix` 行为

```python
# packages/sage-tools/src/sage/tools/cli/commands/dev/main.py:295-302
if all_files:
    cmd.append("--all-files")
    console.print("📂 检查所有文件")
else:
    console.print("📝 检查已暂存的文件（git staged）")  # ← 问题在这！
```

**默认行为**: 只检查 **已暂存（git staged）的文件**

### CI/CD 检查行为

```yaml
# .github/workflows/code-quality.yml:130-135
echo "$CHANGED_FILES" | xargs pre-commit run \
  --config tools/pre-commit-config.yaml \
  --files || {
    # 错误处理...
}
```

**行为**: 检查 **所有变更的文件**（相对于 base 分支），无论是否 staged

### 差异对比

| 场景                     | 本地 `sage-dev quality fix` | CI/CD   |
| ------------------------ | --------------------------- | ------- |
| 已修改但未 staged 的文件 | ❌ 不检查                   | ✅ 检查 |
| 已 staged 的文件         | ✅ 检查                     | ✅ 检查 |
| 已提交但在 PR 中的文件   | ❌ 不检查                   | ✅ 检查 |

## 🎯 问题场景重现

1. 修改文件 `manager.py`（引入语法错误）
1. **不** stage 文件
1. 运行 `sage-dev quality fix`
1. ✅ 本地显示通过（因为没有 staged 文件要检查）
1. Push 到 GitHub
1. ❌ CI/CD 失败（检查到所有变更文件的错误）

## 💡 解决方案

### 方案 A: 短期修复 - 更新文档和提示

**优点**: 不需要改代码，立即可用\
**缺点**: 需要开发者记住使用正确的命令

```bash
# 本地测试 CI/CD 行为（推荐）
sage-dev quality fix --all-files

# 或者使用 check 子命令
sage-dev quality check --all-files
```

**实施**:

1. 更新 `CONTRIBUTING.md` 添加最佳实践说明
1. 在 `sage-dev quality fix` 的输出中添加提示
1. Pre-commit hook 自动检查所有变更文件

### 方案 B: 中期修复 - 改变默认行为

**优点**: 与 CI/CD 完全一致\
**缺点**: 可能破坏现有工作流

```python
# 修改默认行为
@app.command()
def quality(
    # ...
    all_files: bool = typer.Option(
        True,  # ← 改为 True，默认检查所有文件
        "--all-files",
        help="检查所有变更的文件（默认）"
    ),
    staged_only: bool = typer.Option(
        False,  # ← 新增选项
        "--staged-only",
        help="仅检查已暂存的文件"
    ),
```

### 方案 C: 长期方案 - 智能检测

**优点**: 最佳用户体验\
**缺点**: 实现复杂

```python
def _detect_check_scope():
    """智能检测应该检查的范围"""
    # 1. 如果有 staged 文件，检查 staged
    # 2. 如果没有 staged 但有 unstaged 变更，提示用户
    # 3. 如果在 PR 分支，检查所有相对于 base 的变更
    # 4. 默认检查所有文件
```

## 🔧 立即修复步骤

### 对于开发者

```bash
# 1. 检查所有变更文件（推荐，与 CI/CD 一致）
sage-dev quality fix --all-files

# 2. 或者先 stage 所有变更
git add -A
sage-dev quality fix

# 3. 查看修复后的变更
git diff
```

### 对于工具维护者

**优先级 1**: 更新提示信息

```python
# packages/sage-tools/src/sage/tools/cli/commands/dev/main.py
if not all_files:
    console.print("📝 检查已暂存的文件（git staged）")
    console.print(
        "[yellow]💡 提示: CI/CD 会检查所有变更文件，"
        "建议使用 --all-files 与 CI/CD 保持一致[/yellow]"
    )
```

**优先级 2**: 更新文档

- [ ] `CONTRIBUTING.md`: 添加 `--all-files` 推荐
- [ ] `DEVELOPER.md`: 添加本地 vs CI/CD 对比
- [ ] `packages/sage-tools/README.md`: 更新示例

**优先级 3**: 考虑改变默认行为（需要讨论）

## 📊 影响分析

### 当前状态

```bash
# 统计受影响的命令
sage-dev quality          # ❌ 不一致
sage-dev quality fix      # ❌ 不一致
sage-dev quality check    # ❌ 不一致
```

### Pre-commit hook

```bash
# .git/hooks/pre-commit (通过 quickstart.sh 安装)
# 当前行为: 检查 staged 文件 ✅ 正确
# 推荐: 保持现状，commit 时只检查要提交的文件
```

## 🎓 最佳实践

### 提交前检查

```bash
# 1. 修复所有变更文件（推荐）
sage-dev quality fix --all-files

# 2. 运行与 CI/CD 相同的检查
sage-dev quality check --all-files

# 3. Stage 并提交
git add -A
git commit -m "feat: your changes"
```

### CI/CD 对齐

```bash
# 本地模拟 PR 检查
git fetch origin main-dev
sage-dev quality check --all-files

# 检查变更的文件列表
git diff --name-only origin/main-dev...HEAD | grep '\.py$'
```

## 🔗 相关资源

- CI/CD 配置: `.github/workflows/code-quality.yml`
- 本地质量检查实现: `packages/sage-tools/src/sage/tools/cli/commands/dev/main.py`
- Pre-commit 配置: `tools/pre-commit-config.yaml`
- Pre-commit hooks: `packages/sage-tools/src/sage/tools/dev/hooks/`

## 📝 待办事项

- [ ] 决定是否改变默认行为
- [ ] 更新文档（无论采用哪种方案）
- [ ] 添加更清晰的提示信息
- [ ] 考虑添加 `sage-dev ci-check` 命令，完全模拟 CI/CD 行为
- [ ] 更新 `quickstart.sh` 的说明
