# SAGE 安装工具架构决策

**Date**: 2025-11-15\
**Author**: AI Assistant (GitHub Copilot)\
**Summary**: 记录安装工具架构决策，说明为何保留 Shell 脚本方案而非迁移到 Python

## 背景

在开发过程中，我们曾尝试将安装工具迁移到 Python 并集成到 `sage-tools` 包中，但这导致了"先有鸡还是先有蛋"的问题。

## 问题

### 错误的架构（已撤销）

```
packages/sage-tools/src/sage/tools/install/  ❌
├── deps/
│   ├── verify.py
│   └── mirrors.py
└── verify/
    └── install.py
```

**问题**：

1. SAGE 安装前，无法使用 `python -m sage.tools.install`
1. 需要在 `tools/` 和 `packages/` 维护两份代码
1. 增加了不必要的复杂性

## 正确的架构

### 原则

1. **安装工具应该独立于 SAGE 包**

   - 必须在 SAGE 安装前就能使用
   - 不应该依赖任何 SAGE 包

1. **Shell 脚本是最佳选择**

   - 跨平台（bash 在所有 Unix 系统都可用）
   - 不需要额外依赖
   - 直接调用系统命令
   - 已经过充分测试

1. **Python 作为可选辅助**

   - 仅在 Shell 不便实现时使用
   - 必须作为独立脚本（不依赖 sage 包）
   - Shell 脚本可选择性调用

### 目录结构

```
tools/install/
├── quickstart.sh              # 主安装脚本
├── manage.sh                  # 管理工具
├── display_tools/             # 显示工具
├── download_tools/            # 下载工具
├── examination_tools/         # 检查工具
│   ├── dependency_verification.sh
│   ├── mirror_selector.sh
│   ├── install_verification.sh
│   └── ...
├── fixes/                     # 修复工具
└── tests/                     # 测试脚本
```

### sage-tools 的定位

`packages/sage-tools/` 专注于：

- ✅ 开发工具 (`sage-dev`)
- ✅ CLI 工具 (pipeline builder, chat, etc.)
- ✅ 代码质量工具
- ✅ 项目管理工具
- ❌ **不包含** 安装相关的工具

## 决策记录

### 2025-11-15: 撤销 Python 安装工具迁移

**决定**：撤销将安装工具迁移到 `sage-tools` 的尝试

**原因**：

1. "先有鸡还是先有蛋"问题
1. 代码重复
1. 增加复杂性而无实际收益

**撤销的提交**：

- `e253f301` - feat: 添加 Python 版本的安装工具模块
- `0a2d8e07` - chore: 添加工具脚本的可执行权限

**保留**：

- Shell 脚本继续作为主要的安装工具
- 现有的测试和文档

## 未来考虑

如果确实需要 Python 改进某些功能：

1. **创建独立的 Python 辅助脚本**

   ```
   tools/install/python_helpers/  （可选）
   ├── __init__.py
   ├── checksum.py         # 可被 Shell 调用
   └── mirror_test.py      # 可被 Shell 调用
   ```

1. **调用方式**

   ```bash
   # 在 Shell 脚本中
   python tools/install/python_helpers/checksum.py file.whl
   ```

1. **要求**

   - 不依赖任何 sage 包
   - 可独立运行
   - 仅使用 Python 标准库（或明确声明依赖）

## 总结

- ✅ **Shell 脚本** 是安装工具的最佳选择
- ✅ **sage-tools** 专注于开发和已安装后的功能
- ✅ **保持简单** 比过度设计更重要
- ❌ 不要在 `packages/` 中放置安装相关的工具

## 参考

- 相关讨论：GitHub Issue #XXX
- 测试结果：所有 Shell 脚本测试通过
- 文档：docs/TROUBLESHOOTING.md, docs/INSTALLATION_VALIDATION.md
