# SAGE Tools

## 📋 Overview

SAGE Tools 提供了一整套开发、测试、部署和维护工具，帮助开发者高效地管理 SAGE 项目的全生命周期。

## 🧭 Governance / 团队协作制度

- `docs/governance/TEAM.md`
- `docs/governance/MAINTAINERS.md`
- `docs/governance/DEVELOPER_GUIDE.md`
- `docs/governance/PR_CHECKLIST.md`
- `docs/governance/SELF_HOSTED_RUNNER.md`
- `docs/governance/TODO.md`

## 🛠️ Features

### 🔧 Development Toolkit (`sage.dev`)

- Automated testing with pytest integration
- Code quality tools (black, isort, mypy, ruff)
- Package management and publishing
- Performance profiling and benchmarking
- Documentation generation tools
- **Git Hooks Management** - Install and manage pre-commit hooks

### 📦 Package Management

- Monorepo package dependency resolution
- Build and release automation
- Version management utilities
- Distribution packaging tools

### 🧪 Testing & Quality

- Unit test execution and reporting
- Code coverage analysis
- Performance benchmarking
- Quality metrics collection
- **Examples testing framework** (development environment only)

### 🪝 Git Hooks Management

**Integrated Git hooks for code quality and compliance:**

- Pre-commit hooks for code quality checks (black, isort, ruff, mypy)
- Architecture compliance validation (layer dependencies, import paths)
- Documentation standards checking
- Easy install/uninstall with `sage-dev hooks` commands

### 🔬 Examples Testing (Dev Environment Only)

**Note**: Examples testing tools require a development environment with access to the `examples/`
directory.

- Automated examples discovery and analysis
- Category-based testing (tutorials, RAG, memory, etc.)
- Dependency validation
- Runtime estimation and timeout management
- Detailed test reporting

See [Examples Testing README](src/sage/tools/dev/examples/README.md) for details.

### 📊 Analysis & Reporting

- Architecture validation tools
- Dev notes organization
- Documentation quality checker
- Code metrics and statistics

### 🐙 GitHub Issues Management (Extracted)

**Note**: GitHub Issues management functionality has been extracted into a separate project:
[sage-github-manager](https://github.com/intellistream/sage-github-manager)

```bash
# Install the standalone tool
pip install sage-github-manager

# Use it independently
github-manager download
github-manager stats
github-manager ai --action analyze
```

See the [sage-github-manager documentation](https://github.com/intellistream/sage-github-manager)
for details.

## 🚀 Installation

### For End Users (PyPI)

```bash
# Install from PyPI
pip install isage-tools

# Install with CLI support
pip install isage-tools[cli]

# Install with full development tools
pip install isage-tools[dev]
```

### For Developers (Source)

```bash
# Clone SAGE repository
git clone https://github.com/intellistream/SAGE
cd SAGE

# Install in development mode
pip install -e packages/sage-tools[dev]

# This enables all features including Examples testing
```

**Note**: Some features (like Examples testing) are only available when installed from source in a
development environment.

## 📖 Quick Start

### Code Quality Checks

SAGE Tools 提供了一套集成的代码质量检查工具：

```bash
# 运行所有质量检查（推荐）
sage-dev quality

# 检查所有文件
sage-dev quality --all-files

# 自定义检查选项
sage-dev quality --no-architecture  # 跳过架构检查
sage-dev quality --readme            # 包含 README 检查
sage-dev quality --warn-only         # 只警告不中断
```

### Git Hooks Management

管理 Git pre-commit hooks 用于代码质量和合规性检查：

```bash
# 安装 Git hooks
sage-dev maintain hooks install

# 安装（静默模式）
sage-dev maintain hooks install --quiet

# 查看 hooks 状态
sage-dev maintain hooks status

# 卸载 Git hooks
sage-dev maintain hooks uninstall

# 重新安装（更新到最新版本）
sage-dev maintain hooks reinstall
```

**安装后的自动检查包括:**

- 代码格式化和质量检查（black, isort, ruff, mypy）
- 架构合规性验证（包依赖、导入路径）
- 文档规范检查

**使用提示:**

```bash
# 正常提交（运行所有检查）
git commit -m "your message"

# 跳过 hooks 检查（不推荐）
git commit --no-verify -m "your message"
```

### Architecture & Documentation Checks

独立运行特定检查：

```bash
# 查看架构信息
sage-dev architecture                    # 显示完整架构定义
sage-dev architecture --package sage-kernel  # 查看特定包的层级和依赖
sage-dev architecture --format json      # JSON 格式输出
sage-dev architecture --format markdown  # Markdown 格式输出
sage-dev architecture --no-dependencies  # 只显示层级定义

# 架构合规性检查
sage-dev check-architecture              # 检查所有文件
sage-dev check-architecture --changed-only  # 仅检查变更

# 文档规范检查
sage-dev quality devnotes                # 检查所有文档
sage-dev quality devnotes --warn-only    # 只警告不中断

# 包 README 质量检查
sage-dev check-readme                    # 检查所有包
sage-dev check-readme sage-common        # 检查特定包
sage-dev check-readme --report           # 生成详细报告
sage-dev check-readme sage-libs --fix    # 交互式修复

# 运行所有检查（便捷命令）
sage-dev check-all                       # 架构 + 文档 + README
sage-dev check-all --changed-only        # 仅检查变更
sage-dev check-all --continue-on-error   # 出错继续执行
```

### Examples Testing (Development Environment Only)

Test and validate example code in the `examples/` directory:

```bash
# Analyze examples structure
sage-dev examples analyze

# Run quick tests
sage-dev examples test --quick

# Test specific category
sage-dev examples test --category tutorials

# Check intermediate results placement
sage-dev examples check

# Show development environment info
sage-dev examples info
```

**Note**: Examples testing requires a development environment (source installation). See
[Examples Testing Guide](src/sage/tools/dev/examples/README.md) for details.

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

### Using Quality Checkers (Python API)

```python
from sage.tools.dev.tools import (
    ArchitectureChecker,
    DevNotesChecker,
    PackageREADMEChecker,
)

# 架构检查
checker = ArchitectureChecker(root_dir=".")
result = checker.check_all()
if not result.passed:
    for violation in result.violations:
        print(f"{violation.file_path}: {violation.message}")

# 文档检查
checker = DevNotesChecker(root_dir=".")
result = checker.check_all()

# README 检查
checker = PackageREADMEChecker(root_dir=".")
results = checker.check_all()
for r in results:
    print(f"{r.package_name}: {r.score}/100")
```

## 🎯 Quality Check Features

### Architecture Compliance Checker

检查 SAGE 分层架构合规性：

- ✅ 包依赖规则验证（L1-L5 分层）
- ✅ 导入路径合规性检查
- ✅ 模块结构规范验证
- ✅ 跨层依赖检测

**使用场景**:

- Pre-commit hooks 自动检查
- CI/CD 流程集成
- 开发过程中手动检查

### Documentation Checker

检查开发文档规范：

- ✅ 文档分类正确性（architecture, ci-cd, migration 等）
- ✅ 元数据完整性（Date, Author, Summary）
- ✅ 文件名规范检查
- ✅ 目录结构验证

**使用场景**:

- 提交文档前检查
- 批量文档整理
- 文档质量审核

### Package README Quality Checker

检查各包 README 文档质量：

- ✅ README 文件存在性
- ✅ 必需章节完整性
- ✅ 文档结构规范
- ✅ 质量评分（0-100）

**使用场景**:

- 包发布前检查
- 文档质量评估
- 交互式文档改进

## 🔧 Integration

### Git Hooks

通过 `sage-dev maintain hooks` 命令安装和管理 Git pre-commit hooks：

```bash
# 安装 hooks（自动或手动）
./quickstart.sh                       # 自动安装（推荐）
sage-dev maintain hooks install       # 手动安装

# 提交时自动运行检查
git commit -m "your message"
# → 自动运行代码质量检查、架构检查、文档检查

# 查看 hooks 状态
sage-dev maintain hooks status

# 卸载 hooks
sage-dev maintain hooks uninstall
```

### CI/CD Integration

在 GitHub Actions 或其他 CI 系统中使用：

```yaml
- name: Quality Checks
  run: |
    pip install -e packages/sage-tools
    sage-dev quality --all-files

- name: Architecture Check
  run: sage-dev check-architecture

- name: Documentation Check
  run: sage-dev check-devnotes
```

## 📄 License

MIT License - see the [LICENSE](../../LICENSE) file for details.

## 📄 License

MIT License - see [LICENSE](../../LICENSE) for details.
