# Developer Guide

Welcome to the sage-development guide! This document will help you get started with contributing to
SAGE.

## Table of Contents

- [Development Setup](#development-setup)
  - [Prerequisites](#prerequisites)
  - [Initial Setup](#initial-setup)
  - [Submodule Management](#submodule-management)
- [Development Workflow](#development-workflow)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Documentation](#documentation)
- [Release Process](#release-process)

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- (Optional) Conda for environment management

### Quick Start for Contributors

**🔧 作为框架贡献者，推荐使用 `dev` 模式安装：**

```bash
# Clone repository
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# Switch to development branch
git checkout main-dev

# One-command setup for contributors (recommended)
./quickstart.sh --dev --yes
```

**`--dev` 模式会自动：**

- ✅ 同步所有 submodules（无需手动运行 `./manage.sh`）
- ✅ 安装所有开发依赖（pytest, pre-commit, 代码检查工具等）
- ✅ 配置 Git hooks（自动代码质量检查）
- ✅ 安装 sage-dev 工具（用于维护和测试）

> 💡 **不确定该选哪种模式？** 请参考
> [README.md 中的安装模式决策树](./README.md#-%E5%BA%94%E8%AF%A5%E9%80%89%E6%8B%A9%E5%93%AA%E7%A7%8D%E5%AE%89%E8%A3%85%E6%A8%A1%E5%BC%8F)
> 了解 core/standard/full/dev 的区别。

### Initial Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/intellistream/SAGE.git
   cd SAGE
   ```

1. **Switch to development branch**

   ```bash
   git checkout main-dev
   ```

1. **Recommended: Use quickstart with dev mode**

   ```bash
   # This is the easiest way for contributors
   ./quickstart.sh --dev --yes
   ```

   **Or, if you prefer manual setup:**

   a. **Initialize submodules**

   ```bash
   # Use the maintenance tool (recommended)
   ./tools/maintenance/sage-maintenance.sh submodule init

   # This will:
   # - Initialize all submodules
   # - Automatically switch to the correct branch (main-dev)
   ```

   b. **Run the developer setup script**

   ```bash
   ./tools/dev.sh setup
   ```

   This will:

   - Install pre-commit hooks
   - Install SAGE in development mode
   - Install all development dependencies

1. **Verify the setup**

   ```bash
   ./tools/dev.sh validate

   # Check project health
   ./tools/maintenance/sage-maintenance.sh doctor
   ```

### Submodule Management

SAGE uses Git submodules for modular components (docs-public, sageDB, sageLLM, sageFlow). Use the
maintenance tool for all submodule operations:

#### Quick Reference

```bash
# Initialize submodules (first time or after clone)
./tools/maintenance/sage-maintenance.sh submodule init

# Check submodule status
./tools/maintenance/sage-maintenance.sh submodule status

# Switch submodule branches (after switching SAGE branch)
./tools/maintenance/sage-maintenance.sh submodule switch

# Update submodules to latest remote version
./tools/maintenance/sage-maintenance.sh submodule update
```

#### Branch Matching Rules

| SAGE Branch    | Submodule Branch | Usage               |
| -------------- | ---------------- | ------------------- |
| `main`         | `main`           | Stable releases     |
| `main-dev`     | `main-dev`       | Development         |
| Other branches | `main-dev`       | Default development |

#### Important Notes

⚠️ **Always use the maintenance tool instead of raw Git commands:**

```bash
# ❌ Don't use (causes detached HEAD)
git submodule update --init

# ✅ Use this instead
./tools/maintenance/sage-maintenance.sh submodule init
```

#### Troubleshooting Submodules

**Problem: Submodules in detached HEAD state**

```bash
# Fix: Switch to correct branch
./tools/maintenance/sage-maintenance.sh submodule switch
```

**Problem: Submodule conflicts during merge**

```bash
# Fix: Resolve conflicts automatically
./tools/maintenance/sage-maintenance.sh submodule fix-conflict
```

**Problem: Old submodule configuration**

```bash
# Fix: Clean up old config
./tools/maintenance/sage-maintenance.sh submodule cleanup
```

For more details, see [tools/maintenance/README.md](tools/maintenance/README.md).

> **💡 提示：** 使用 `./quickstart.sh --dev --yes` 会自动处理所有 submodule 相关操作，无需手动运行上述命令。

### Alternative: Manual Setup

If you prefer manual setup:

```bash
# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Install development tools
pip install black isort ruff mypy pytest pytest-cov
```

## Development Workflow

### Using the Dev Helper Script

The `scripts/dev.sh` script provides common development commands:

```bash
# Format code
./tools/dev.sh format

# Run linters
./tools/dev.sh lint

# Run tests
./tools/dev.sh test

# Run all checks before committing
./tools/dev.sh validate

# Clean build artifacts
./tools/dev.sh clean

# Build documentation
./tools/dev.sh docs

# Get help
./tools/dev.sh help
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. They include:

- **Code Formatting**: black, isort
- **Linting**: ruff, mypy
- **Shell Scripts**: shellcheck
- **File Checks**: trailing whitespace, end-of-file fixer, etc.
- **Security**: detect-secrets

To run pre-commit manually:

```bash
pre-commit run --all-files
```

To skip pre-commit hooks temporarily (not recommended):

```bash
git commit --no-verify
```

## Code Quality

### Pre-commit Hooks Configuration

SAGE uses a **non-standard location** for pre-commit configuration:

- **Actual configuration**: `tools/pre-commit-config.yaml`
- **Standard location symlink**: `.pre-commit-config.yaml` → `tools/pre-commit-config.yaml`

**Why tools/ directory?**

- Centralized management with other dev tools (`dev.sh`, `maintenance/`)
- Keeps project root clean and organized
- Easier to maintain development tooling

**Installation and Usage:**

```bash
# Recommended: Use sage-dev (auto-detects correct config)
sage-dev maintain hooks install

# Alternative: Standard pre-commit (uses symlink)
pre-commit install

# Manual: Explicit config path
pre-commit install --config tools/pre-commit-config.yaml

# Run checks manually (same as CI)
pre-commit run --all-files
```

**Local and CI Consistency:**

Both local Git hooks and GitHub Actions CI use the **same configuration file**
(`tools/pre-commit-config.yaml`):

- ✅ Local: Uses `.pre-commit-config.yaml` symlink → `tools/pre-commit-config.yaml`
- ✅ CI: Uses `--config tools/pre-commit-config.yaml` explicitly
- ✅ Result: Identical checks locally and in CI

**Verify your setup:**

```bash
# Check hook configuration
cat .git/hooks/pre-commit | grep "ARGS="
# Expected: ARGS=(hook-impl --config=tools/pre-commit-config.yaml ...)

# Run full checks (matches CI exactly)
pre-commit run --all-files

# Check individual tools
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

### Code Formatting

We use **Black** and **isort** for consistent code formatting:

```bash
# Format all code
./tools/dev.sh format

# Or manually:
black packages/ examples/ scripts/ --line-length 100
isort packages/ examples/ scripts/ --profile black --line-length 100
```

**Configuration**:

- Line length: 100 characters
- isort profile: black (for compatibility)

### Linting

We use **Ruff** for fast linting and **mypy** for type checking:

```bash
# Run all linters
./tools/dev.sh lint

# Or run individually:
ruff check packages/ examples/ scripts/
mypy packages/ --ignore-missing-imports
```

**Ruff Configuration** (in `pyproject.toml` or `.ruff.toml`):

- Line length: 100
- Target Python version: 3.10
- Enable modern Python features

### Shell Scripts

Shell scripts are checked with **shellcheck**:

```bash
shellcheck scripts/**/*.sh tools/**/*.sh
```

## Testing

### Running Tests

```bash
# Run all tests
./tools/dev.sh test

# Run unit tests only
./tools/dev.sh test-unit

# Run integration tests only
./tools/dev.sh test-integration

# Run specific test file
pytest tests/test_specific.py -v

# Run with coverage report
pytest tests/ --cov=packages --cov-report=html
```

### Writing Tests

- Place unit tests in `packages/*/tests/unit/`
- Place integration tests in `packages/*/tests/integration/`
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Use pytest fixtures for common setup
- Mark integration tests with `@pytest.mark.integration`

Example:

```python
import pytest
from sage.core.api.local_environment import LocalEnvironment


def test_local_environment_initialization_creates_instance():
    """Test that LocalEnvironment can be initialized."""
    env = LocalEnvironment("test_env")
    assert env is not None
    assert env.name == "test_env"


@pytest.mark.integration
def test_pipeline_execution_with_real_data():
    """Integration test with actual data processing."""
    # Your integration test here
    pass
```

## Documentation

### Building Documentation

```bash
# Build documentation
./tools/dev.sh docs

# Serve documentation locally
./tools/dev.sh serve-docs
```

### Writing Documentation

1. **API Documentation**: Use docstrings with Google style

   ```python
   def example_function(param1: str, param2: int) -> bool:
       """Brief description of function.

       Detailed description of what the function does.

       Args:
           param1: Description of param1
           param2: Description of param2

       Returns:
           Description of return value

       Raises:
           ValueError: When invalid input is provided

       Examples:
           >>> example_function("test", 42)
           True
       """
       pass
   ```

1. **User Guides**: Place in `docs-public/docs_src/`

1. **Dev Notes**: Use the template in `docs/dev-notes/TEMPLATE.md`

### Creating Dev Notes

When documenting fixes or features:

```bash
# Copy the template
cp docs/dev-notes/TEMPLATE.md docs/dev-notes/<category>/<FEATURE_NAME>_<ISSUE_NUM>.md

# Fill in the template
# See docs/dev-notes/QUICK_START.md for guidance
```

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

### Creating a Release

1. **Update CHANGELOG.md**

   - Move items from `[Unreleased]` to new version section
   - Add release date
   - Update comparison links

1. **Update version numbers**

   - Update version in `setup.py` or `pyproject.toml`
   - Update version in `__init__.py` files

1. **Run validation**

   ```bash
   ./tools/dev.sh validate
   ```

1. **Create git tag**

   ```bash
   git tag -a v0.2.0 -m "Release version 0.2.0"
   git push origin v0.2.0
   ```

1. **Create GitHub release**

   - Go to GitHub releases page
   - Create new release from tag
   - Copy CHANGELOG entry to release notes

1. **Publish to PyPI** (maintainers only)

   ```bash
   python -m build
   python -m twine upload dist/*
   ```

## Contributing Guidelines

### Before Starting

1. Check existing issues and PRs to avoid duplicates
1. For large changes, open an issue first to discuss
1. Read `CONTRIBUTING.md` for detailed guidelines

### Pull Request Process

1. **Create a feature branch**

   ```bash
   git checkout -b feature/my-feature
   # or
   git checkout -b fix/issue-123
   ```

1. **Make your changes**

   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation as needed

1. **Run validation**

   ```bash
   ./tools/dev.sh validate
   ```

1. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):

   - `feat:` New features
   - `fix:` Bug fixes
   - `docs:` Documentation changes
   - `style:` Code style changes (formatting)
   - `refactor:` Code refactoring
   - `test:` Test changes
   - `chore:` Build/tooling changes

1. **Push and create PR**

   ```bash
   git push origin feature/my-feature
   ```

   Then create a pull request on GitHub.

### Code Review

- All PRs require at least one approval
- Address review comments promptly
- Keep PR scope focused and manageable
- Update PR description if scope changes

## Getting Help

- **Documentation**: Check `docs/` and `docs-public/`
- **Examples**: Look at `examples/` directory
- **Issues**: Search existing issues or create new one
- **Community**: Join our
  [Slack](https://join.slack.com/t/intellistream/shared_invite/zt-2qayp8bs7-v4F71ge0RkO_rn34hBDWQg)
  or [WeChat](./docs/COMMUNITY.md)

## Useful Resources

- [Architecture Diagram](docs/images/architecture.svg)
- [Dev Notes Template](docs/dev-notes/TEMPLATE.md)
- [Dev Notes Quick Start](docs/dev-notes/QUICK_START.md)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

______________________________________________________________________

Thank you for contributing to SAGE! 🚀
