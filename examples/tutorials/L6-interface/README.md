# L6: Interface Layer - 接口层

## 📋 概述

**对应包**：`sage-studio`, `sage-tools`, `sage-cli`

L6 是 SAGE 架构的**顶层接口层**，提供用户直接交互的多种工具：

- 🎨 **Web UI** (sage-studio)：可视化管道编辑器
- 🛠️ **开发工具** (sage-tools)：测试、代码质量、包管理等
- 💻 **命令行接口** (sage-cli)：提供 `sage` 命令行工具

## � L6 包详解

### 1️⃣ sage-studio - Web UI

**功能**：

- 可视化管道设计器
- 拖拽式操作符连接
- 实时预览和调试
- 管道部署和监控

**适用场景**：

- 无代码/低代码开发
- 快速原型验证
- 团队协作开发
- 生产环境监控

### 2️⃣ sage-tools - 开发工具集

**功能**：

- `fix-code-quality.sh`：代码质量检查和自动修复
- `pytest`：单元测试框架配置
- `ruff`：Python 代码检查
- `mypy`：类型检查
- 包管理和依赖分析

**适用场景**：

- 开发环境配置
- CI/CD 流程集成
- 代码质量保证
- 包维护和发布

### 3️⃣ sage-cli - 命令行接口

**功能**：

- `sage` 命令：统一的命令行入口
- 项目初始化和脚手架
- 管道运行和调试
- 配置管理

**适用场景**：

- 快速启动项目
- 脚本化自动化
- 远程服务器部署
- 开发者工作流

## 🎯 学习目标

- 理解 SAGE 的三种用户界面（Web、CLI、工具集）
- 掌握可视化管道编辑
- 使用命令行快速开发和部署
- 使用开发工具提升代码质量

## 📚 示例列表

> ⚠️ **注意**：L6 示例即将添加

### 规划中的示例

#### sage-studio 示例

- [ ] `web_pipeline_editor.md` - 使用 Web UI 创建管道
- [ ] `dashboard_monitoring.md` - 生产环境监控面板
- [ ] `collaborative_development.md` - 团队协作开发

#### sage-cli 示例

- [ ] `cli_quickstart.py` - 使用 `sage` 命令快速开始
- [ ] `cli_project_init.sh` - 项目初始化
- [ ] `cli_pipeline_run.sh` - 运行和调试管道

#### sage-tools 示例

- [ ] `setup_dev_environment.sh` - 配置开发环境
- [ ] `run_code_quality_checks.sh` - 运行代码检查
- [ ] `package_management.md` - 包管理最佳实践

## � 依赖关系

```
L6 (Interface: studio + tools + cli)
 ↓ 可以使用
L5 (Apps) + L4 (Middleware) + L3 (Kernel/Libs) + L2 (Platform) + L1 (Common)
```

L6 是最顶层，可以使用所有下层的功能。

## 🚀 快速开始

### 使用 sage-cli

```bash
# 安装 sage-cli（假设已安装 SAGE）
# pip install sage-cli

# 初始化新项目
sage init my-rag-app --template rag

# 运行管道
sage run pipeline.py

# 查看帮助
sage --help
```

### 使用 sage-studio

```bash
# 启动 Web UI（假设已安装）
# sage-studio start

# 访问 http://localhost:8080
# 在浏览器中打开管道编辑器
```

### 使用 sage-tools

```bash
# 运行代码质量检查
cd /path/to/sage
./tools/fix-code-quality.sh

# 运行测试
pytest

# 类型检查
./tools/mypy-wrapper.sh
```

## 💡 使用建议

### 何时使用 sage-studio

- ✅ 快速原型验证
- ✅ 团队协作
- ✅ 非技术用户参与
- ✅ 可视化调试

### 何时使用 sage-cli

- ✅ 快速启动项目
- ✅ 脚本自动化
- ✅ CI/CD 集成
- ✅ 远程部署

### 何时使用 sage-tools

- ✅ 开发环境配置
- ✅ 代码质量检查
- ✅ 包维护
- ✅ 贡献代码

## 📚 相关文档

- [SAGE 包架构](../../../../docs-public/docs_src/dev-notes/package-architecture.md)
- [开发者指南](../../../../DEVELOPER.md)
- [贡献指南](../../../../CONTRIBUTING.md)
