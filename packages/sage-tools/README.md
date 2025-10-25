# SAGE Tools

## 📋 Overview

SAGE Tools 提供了一整套开发、测试、部署和维护工具，帮助开发者高效地管理 SAGE 项目的全生命周期。

## 🛠️ Features

### � Development Toolkit (`sage.dev`)

- Automated testing with pytest integration
- Code quality tools (black, isort, mypy, ruff)
- Package management and publishing
- Performance profiling and benchmarking
- Documentation generation tools

### � Package Management

- Monorepo package dependency resolution
- Build and release automation
- Version management utilities
- Distribution packaging tools

### 🧪 Testing & Quality

- Unit test execution and reporting
- Code coverage analysis
- Performance benchmarking
- Quality metrics collection

### 📊 Analysis & Reporting

- Architecture validation tools
- Dev notes organization
- Documentation quality checker
- Code metrics and statistics

## 🚀 Installation

```bash
# 安装开发工具包
pip install -e packages/sage-tools

# 或使用 sage dev 命令
sage dev install sage-tools
```

## 📖 Quick Start

### Using Development Tools

```bash
# 运行测试
sage-dev test

# 代码质量分析
sage-dev analyze

# 包管理
sage-dev package build
sage-dev package publish

# 生成报告
sage-dev report coverage
sage-dev report performance
```

### Using Quality Checkers

```python
from sage.tools import architecture_checker, devnotes_checker

# 检查架构一致性
architecture_checker.validate_project()

# 检查开发文档质量
devnotes_checker.check_all()
```

## 📄 License

MIT License - see the [LICENSE](../../LICENSE) file for details.

## 📄 License

MIT License - see [LICENSE](../../LICENSE) for details.
