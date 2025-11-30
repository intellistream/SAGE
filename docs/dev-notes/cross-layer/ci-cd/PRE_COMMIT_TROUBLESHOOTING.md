# Pre-commit Hooks 故障排除指南

**Date**: 2024-10-29  
**Author**: SAGE Team  
**Summary**: Pre-commit hooks 的常见问题诊断和故障排除指南

> **注意**: 本文档已整合到 [code-quality-guide.md](./code-quality-guide.md)
> 请参考主文档获取完整的配置说明和最佳实践。

## 快速诊断

如果 pre-commit hooks 没有运行：

```bash
# 运行诊断脚本
./tools/verify-precommit.sh
```

## 常见问题

### 1. Hooks 没有运行

**症状**: 提交时没有看到 black/ruff 等检查

**解决**:
```bash
pre-commit install --config tools/pre-commit-config.yaml -f
```

### 2. 代码格式反复变化

**症状**: 每次运行都修改相同的文件

**已解决**: 现在所有包使用统一的 `tools/ruff.toml` 配置

### 3. CI/CD 失败但本地没问题

**原因**: 可能使用了 `git commit -n` 跳过了检查

**解决**: 不要使用 `-n` 或 `--no-verify` 参数

## 详细文档

完整的配置说明、工作流程和最佳实践，请参考：
- [代码质量配置指南](./code-quality-guide.md)

## 问题描述

在 CI/CD 流程中，代码质量检查（black、isort、ruff）失败，但本地提交时没有发现这些问题。

## 根本原因

Pre-commit hooks 虽然已安装，但在本地提交时**没有被触发**或**被跳过**。常见原因包括：

### 1. 使用了 `--no-verify` 参数

```bash
# ❌ 这会跳过所有 pre-commit hooks
git commit -n -m "message"
git commit --no-verify -m "message"

# ✅ 正确做法
git commit -m "message"
```

### 2. Pre-commit 环境未正确初始化

即使 `.git/hooks/pre-commit` 文件存在，pre-commit 的虚拟环境可能没有正确设置。

### 3. 只检查已 staged 的文件

Pre-commit 只会检查通过 `git add` 添加到暂存区的文件。如果修改了文件但没有 stage，hooks 不会检查这些文件。

## 解决方案

### 快速修复（立即修复所有问题）

```bash
# 运行代码质量修复脚本
./tools/fix-code-quality.sh
```

这个脚本会：
1. 运行 black 格式化所有 Python 文件
2. 运行 isort 排序所有导入语句
3. 运行 ruff 修复常见的代码问题

### 重新安装 Pre-commit Hooks

```bash
# 1. 确保 pre-commit 已安装
pip install pre-commit

# 2. 重新安装 hooks（使用项目配置文件）
pre-commit install --config tools/pre-commit-config.yaml

# 3. 验证安装
pre-commit run --all-files --config tools/pre-commit-config.yaml
```

### 在每次提交前手动运行检查

```bash
# 运行所有检查
pre-commit run --all-files --config tools/pre-commit-config.yaml

# 只运行特定检查
pre-commit run black --all-files --config tools/pre-commit-config.yaml
pre-commit run isort --all-files --config tools/pre-commit-config.yaml
pre-commit run ruff --all-files --config tools/pre-commit-config.yaml
```

## 最佳实践

### 1. 提交前检查清单

- [ ] 确保所有修改的文件都已 `git add`
- [ ] 不要使用 `-n` 或 `--no-verify` 参数
- [ ] 在 push 前运行 `pre-commit run --all-files`
- [ ] 检查 pre-commit 输出，确保没有错误

### 2. 编辑器集成

#### VS Code

安装扩展：
- Black Formatter
- isort
- Ruff

在 `.vscode/settings.json` 中配置：

```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "isort.args": ["--profile", "black", "--line-length", "100"],
  "black-formatter.args": ["--line-length", "100"]
}
```

#### PyCharm

1. File → Settings → Tools → Black
2. 启用 "Run Black on save"
3. 配置 isort：File → Settings → Tools → External Tools

### 3. 团队协作

在项目 README 或 CONTRIBUTING 文档中明确说明：

```markdown
## 开发环境设置

1. 安装依赖：`pip install -r requirements.txt`
2. 安装 pre-commit hooks：`pre-commit install --config tools/pre-commit-config.yaml`
3. 验证设置：`pre-commit run --all-files --config tools/pre-commit-config.yaml`

## 提交代码

- 不要使用 `git commit -n` 或 `--no-verify`
- 确保 pre-commit hooks 通过所有检查
- 在 push 前运行：`./tools/fix-code-quality.sh`
```

## 调试 Pre-commit

### 检查 hook 是否安装

```bash
ls -la .git/hooks/pre-commit
cat .git/hooks/pre-commit
```

### 检查 pre-commit 配置

```bash
pre-commit --version
pre-commit run --all-files --config tools/pre-commit-config.yaml --verbose
```

### 清理并重新安装

```bash
# 清理 pre-commit 缓存
pre-commit clean
pre-commit gc

# 重新安装
pre-commit install --config tools/pre-commit-config.yaml --install-hooks

# 更新 hooks 到最新版本
pre-commit autoupdate --config tools/pre-commit-config.yaml
```

## CI/CD 与本地一致性

为确保 CI/CD 和本地环境使用相同的检查：

1. **使用相同的配置文件**：`tools/pre-commit-config.yaml`
2. **使用相同的工具版本**：定期运行 `pre-commit autoupdate`
3. **在 CI 中使用 pre-commit**：`.github/workflows/ci.yml` 应该运行 `pre-commit run --all-files`

## 工具脚本

项目提供了以下辅助脚本：

- `tools/fix-code-quality.sh` - 自动修复所有代码质量问题
- `tools/mypy-wrapper.sh` - 运行类型检查（警告模式）

## 常见错误

### black 格式化失败

```
black....................................................................Failed
- files were modified by this hook
```

**原因**：代码格式不符合 black 标准

**解决**：black 已自动修复，需要重新 stage 和提交这些文件

### isort 导入排序失败

```
isort....................................................................Failed
- files were modified by this hook
```

**原因**：导入语句顺序不符合 isort 标准

**解决**：isort 已自动修复，需要重新 stage 和提交这些文件

### ruff 检查失败

```
ruff.....................................................................Failed
- exit code: 1
```

**原因**：代码存在 lint 问题（未使用的导入、变量等）

**解决**：ruff 已自动修复大部分问题，少数需要手动修复

## 总结

**核心问题**：Pre-commit hooks 未在本地提交时触发

**核心解决方案**：
1. 重新安装 pre-commit hooks
2. 不要使用 `--no-verify` 参数
3. 提交前运行 `./tools/fix-code-quality.sh`
4. 配置编辑器自动格式化

**预防措施**：
- 团队成员统一安装和配置 pre-commit
- 在 CI/CD 中强制执行相同的检查
- 定期更新 pre-commit hooks 版本
