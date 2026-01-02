# Pre-commit Hooks 配置指南

**Date**: 2024-10-29\
**Author**: SAGE Team\
**Summary**: SAGE 项目的代码质量检查配置说明，包括 Pre-commit hooks 的配置和故障排除

## 📋 概述

本文档说明 SAGE 项目的代码质量检查配置，包括为什么 CI/CD 发现问题但本地没有发现的原因。

## 🎯 问题诊断

### 症状

**CI/CD 失败但本地提交没有检查到问题**

```
black....................................................................Failed
isort....................................................................Failed
ruff.....................................................................Failed
```

### 根本原因

1. **Pre-commit hooks 未触发**

   - 使用了 `git commit -n` 或 `--no-verify` 跳过检查
   - IDE 或 Git 客户端默认跳过 hooks
   - Pre-commit 环境未正确安装

1. **配置冲突（已解决）**

   - ~~之前 isort 和 ruff 配置不一致，导致互相覆盖~~
   - **现已统一**：所有子包继承根目录 `ruff.toml` 配置

## ✅ 当前配置架构

### 统一配置文件

```
SAGE/
├── tools/
│   ├── ruff.toml                # 根级统一配置（所有包共享）
│   └── pytest.ini               # 根级测试配置
└── packages/
    ├── sage/pyproject.toml      # extend = "../../tools/ruff.toml"
    ├── sage-kernel/pyproject.toml  # extend = "../../tools/ruff.toml"
    ├── sage-libs/pyproject.toml    # extend = "../../tools/ruff.toml"
    └── ...                         # 所有包都继承根配置
```

### Pre-commit 流程

```yaml
# tools/pre-commit-config.yaml
1. black     → 代码格式化
2. ruff      → Lint + Import 排序（替代 isort）
3. mypy      → 类型检查（警告模式）
4. shellcheck → Shell 脚本检查
```

**关键变更**：

- ❌ 移除了 standalone `isort`（避免与 ruff 冲突）
- ✅ 只使用 `ruff` 进行 import 排序（更快，配置统一）

## 🔧 开发工作流

### 初次设置

```bash
# 1. 安装 pre-commit
pip install pre-commit

# 2. 安装 hooks
pre-commit install --config tools/pre-commit-config.yaml

# 3. 验证安装
./tools/verify-precommit.sh
```

### 日常开发

```bash
# 提交前自动检查（推荐）
git add .
git commit -m "message"  # hooks 自动运行

# 或手动运行检查
./tools/fix-code-quality.sh

# 或针对性检查
pre-commit run --all-files --config tools/pre-commit-config.yaml
```

### ⚠️ 注意事项

**❌ 永远不要使用：**

```bash
git commit -n           # 跳过所有 hooks
git commit --no-verify  # 跳过所有 hooks
```

**✅ 正确做法：**

```bash
git commit              # 让 hooks 正常运行
```

## 🛠️ 工具脚本

### `tools/fix-code-quality.sh`

自动修复所有代码质量问题（black、ruff）

```bash
./tools/fix-code-quality.sh
```

### `tools/verify-precommit.sh`

验证 pre-commit 设置是否正确

```bash
./tools/verify-precommit.sh
```

输出示例：

```
✅ pre-commit is installed
✅ pre-commit hook file exists
✅ pre-commit hook is executable
✅ No custom hooks path configured
✅ pre-commit hooks can run successfully
```

## 📝 编辑器集成（可选但推荐）

### VS Code

1. 安装扩展：

   - Black Formatter (`ms-python.black-formatter`)
   - Ruff (`charliermarsh.ruff`)

1. 配置 `.vscode/settings.json`：

```json
{
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "black-formatter.args": ["--line-length", "100"],
  "ruff.configuration": "./tools/ruff.toml"
}
```

### PyCharm

1. File → Settings → Tools → Black

   - 启用 "Run Black on save"
   - Line length: 100

1. File → Settings → Tools → External Tools

   - 添加 Ruff 作为外部工具

## 🔍 故障排除

### Pre-commit 没有运行？

```bash
# 检查安装
./tools/verify-precommit.sh

# 重新安装
pre-commit clean
pre-commit install --config tools/pre-commit-config.yaml -f
```

### 代码格式反复变化？

**原因已解决**：之前是 isort 和 ruff 配置冲突

**当前状态**：所有包使用统一的 `ruff.toml`，不会再反复

### Ruff 报错无法修复？

某些错误需要手动修复，例如：

- `B008`: typer.Option 在参数默认值中使用（需要重构代码）
- 复杂的逻辑问题

运行以查看详情：

```bash
ruff check . --config tools/ruff.toml
```

## 📚 配置文件说明

### `tools/ruff.toml`

根级统一配置，包含：

- 代码风格规则（E, W, F, I, B, C4, UP, C90）
- Import 排序规则（替代 isort）
- 忽略的错误类型
- 文件特定规则

### `tools/pytest.ini`

根级测试配置，包含：

- 测试路径
- 测试标记（markers）
- 过滤警告

### `tools/pre-commit-config.yaml`

Pre-commit hooks 配置，包含：

- black (代码格式化)
- ruff (lint + import sort)
- mypy (类型检查，警告模式)
- shellcheck (shell 脚本)
- 其他通用检查

## 🎓 最佳实践

1. **开发前**：确保 pre-commit 已安装
1. **提交前**：不要跳过 hooks（不用 `-n`）
1. **推送前**：运行 `./tools/fix-code-quality.sh`
1. **配置修改**：只修改 `tools/ruff.toml`，子包自动继承
1. **编辑器**：配置自动格式化，减少手动修复

## 📊 配置演进历史

### v1: 多工具独立配置（已废弃）

- 每个包有自己的 ruff/isort 配置
- isort 和 ruff 同时运行，配置冲突
- **问题**：反复修复，配置不一致

### v2: 统一配置（当前）

- 根目录 `tools/ruff.toml` 统一配置
- 所有包通过 `extend` 继承
- 只用 ruff 处理 import（移除 isort）
- **优点**：配置一致，不再冲突，更快

## 🔗 相关资源

- [Pre-commit 官方文档](https://pre-commit.com/)
- [Ruff 官方文档](https://docs.astral.sh/ruff/)
- [Black 文档](https://black.readthedocs.io/)
- [项目贡献指南](../../../CONTRIBUTING.md)
