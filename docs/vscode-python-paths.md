# VS Code Python 路径自动更新脚本

## 概述

`scripts/update_vscode_python_paths.py` 是一个自动化脚本，用于扫描 `packages` 目录下的所有 Python 包，并自动更新 VS Code 的 `settings.json` 文件中的 Python 分析路径配置。

## 功能特性

- 🔍 **智能扫描**: 自动发现所有包含 `pyproject.toml` 的 Python 包
- 📦 **多层级支持**: 支持 `packages/`, `packages/commercial/`, `packages/tools/` 等多层级目录结构
- 🎯 **优先级处理**: 优先使用 `src/` 目录，其次是包含 `__init__.py` 的目录
- ✅ **自动备份**: 解析错误时自动备份原有配置文件
- 🔧 **完整配置**: 自动设置所有必要的 Python 分析选项

## 使用方法

### 基本使用

```bash
# 在 SAGE 项目根目录下运行
python scripts/update_vscode_python_paths.py
```

### 预期输出

脚本会显示发现的所有 Python 包路径：

```
🔍 Scanning packages directory for Python packages...

✓ Package with src: ./packages/sage-kernel/src
✓ Package with src: ./packages/sage-middleware/src
✓ Package with src: ./packages/sage-userspace/src
✓ Commercial package with src: ./packages/commercial/sage-kernel/src
✓ Commercial package with src: ./packages/commercial/sage-middleware/src
✓ Commercial package with src: ./packages/commercial/sage-userspace/src
✓ Tools package with src: ./packages/tools/sage-cli/src
✓ Tools Python package: ./packages/tools/sage-frontend

📦 Found 8 Python package paths:
   1. ./packages/commercial/sage-kernel/src
   2. ./packages/commercial/sage-middleware/src
   3. ./packages/commercial/sage-userspace/src
   4. ./packages/sage-kernel/src
   5. ./packages/sage-middleware/src
   6. ./packages/sage-userspace/src
   7. ./packages/tools/sage-cli/src
   8. ./packages/tools/sage-frontend

🎉 VS Code Python paths updated successfully!
```

## 扫描规则

### 包发现逻辑

1. **pyproject.toml 包**: 查找所有包含 `pyproject.toml` 的目录，优先使用其 `src/` 子目录
2. **商业包**: 扫描 `packages/commercial/*/src` 目录
3. **工具包**: 扫描 `packages/tools/*/src` 目录和其他 Python 包目录
4. **根级包**: 扫描 `packages/*/src` 目录

### Python 包识别标准

目录被识别为 Python 包的条件：
- 包含 `__init__.py` 文件，或
- 包含 2 个或更多 `.py` 文件

## 生成的配置

脚本会更新 `.vscode/settings.json` 中的以下设置：

```json
{
  "python.analysis.extraPaths": [
    "./packages/commercial/sage-kernel/src",
    "./packages/commercial/sage-middleware/src",
    "./packages/commercial/sage-userspace/src",
    "./packages/sage-kernel/src",
    "./packages/sage-middleware/src",
    "./packages/sage-userspace/src",
    "./packages/tools/sage-cli/src",
    "./packages/tools/sage-frontend",
    "."
  ],
  "python.autoComplete.extraPaths": [...],
  "python.analysis.autoSearchPaths": true,
  "python.analysis.useLibraryCodeForTypes": true,
  "python.analysis.autoImportCompletions": true,
  "pylance.insidersChannel": "off",
  "python.languageServer": "Pylance",
  "python.analysis.typeCheckingMode": "off",
  "python.defaultInterpreterPath": "/usr/bin/python3"
}
```

## 故障排除

### 常见问题

1. **JSON 解析错误**: 脚本会自动备份损坏的配置文件并创建新的
2. **权限问题**: 确保对 `.vscode/` 目录有写权限
3. **包未被发现**: 检查包目录是否包含有效的 Python 文件

### 手动验证

运行脚本后，你可以：

1. 检查 `.vscode/settings.json` 文件内容
2. 在 VS Code 中重新加载窗口 (`Ctrl+Shift+P` -> "Developer: Reload Window")
3. 测试 Python 导入是否正常工作

## 集成到开发流程

建议在以下情况下运行此脚本：

- 添加新的 Python 包到 `packages/` 目录后
- 重构包结构后
- 设置新的开发环境时
- VS Code 无法正确解析导入时

## 相关文件

- `scripts/update_vscode_python_paths.py` - 主脚本
- `.vscode/settings.json` - VS Code 配置文件
- `.vscode/settings.json.backup` - 自动生成的备份文件（如有）
