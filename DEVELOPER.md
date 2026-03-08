# Developer Guide

Welcome to the sage-development guide! This document will help you get started with contributing to
SAGE.

## ⚠️ Installation Note

Use `./quickstart.sh` for installation to ensure consistency across all environments.

______________________________________________________________________

## Table of Contents

- [Development Setup](#development-setup)
  - [Prerequisites](#prerequisites)
  - [Initial Setup](#initial-setup)
  - [Submodule Management](#submodule-management)
- [Dependency Management](#dependency-management)
  - [Core Dependencies Architecture](#core-dependencies-architecture)
  - [Per-Layer Dependencies](#per-layer-dependencies)
  - [Feature Modules](#feature-modules)
  - [Installation Examples](#installation-examples)
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

- ✅ 安装所有开发依赖（pytest, pre-commit, 代码检查工具等）
- ✅ 配置 Git hooks（自动代码质量检查）
- ✅ 安装 sage-dev 工具（用于维护和测试）
- ✅ 尽量将同级工作区本地子仓库安装为 editable（`-e`，若仓库存在）

**`--standard` 模式会自动：**

- ✅ 安装本地根目录 `isage` meta 包
- ✅ 子包依赖按版本约束从 PyPI 解析（稳定/发布导向）

> 💡 **注意**: 用户文档已迁移到独立的 [sage-docs](https://github.com/intellistream/sage-docs) 仓库。### Initial Setup

1. Clone and switch to development branch

   ```bash
   git clone https://github.com/intellistream/SAGE.git && cd SAGE
   git checkout main-dev
   ```

1. Install development environment

   ```bash
   ./quickstart.sh --dev --yes
   ```

> 💡 For multi-folder VS Code editing, clone `sage-docs` repository in the parent directory pre-commit
> install

# Install development tools

pip install black isort ruff mypy pytest pytest-cov

````

______________________________________________________________________

## Dependency Management

### Layer Ownership Matrix (Wave A Baseline)

For cross-repo boundary refactor reviews, use the canonical ownership matrix:

- [sage-docs architecture/layer-ownership](https://intellistream.github.io/sage-docs/architecture/layer-ownership/)

This matrix defines current workspace L1-L4 ownership, forbidden dependency direction, violation examples, and
remediation priority for Phase 1, including independent sub-repo coordination and `sagellm`
capability boundaries.

### Core Dependencies Architecture

SAGE follows a **minimalist core dependency strategy** with a **modular feature model**:

- **Core Dependencies** (`dependencies`): Only packages necessary for base functionality
- **Dev Dependencies** (`dev` extra): Testing tools, linters, and development utilities
- **Feature Modules**: Functionality available through independent PyPI packages

**Key Principle**: We maintain **minimal core** to reduce bloat and installation time. Specialized functionality is available through independent packages that users can install as needed.

### Per-Layer Dependencies

Current workspace numbering is normalized to the actively maintained main repos:

#### L1. sage-common (Foundation)

**Core**:
- `pyyaml>=6.0` - Configuration files
- `psutil>=6.1.0` - System information
- `dill>=0.3.8` - Object serialization
- `numpy>=1.26.0,<2.3.0` - Numerical computation
- `pydantic>=2.10.0,<3.0.0` - Data validation
- `platformdirs>=4.0.0` - User paths

**Also owns now**: former `sage-platform` abstractions and the shared interface surface previously
split into `sage-libs`.

#### L2. sage-kernel (Runtime / Scheduler)

**Core**:
- `isage-flownet>=0.1.0` ⭐ **Distributed runtime/scheduling (mandatory)**
- `fastapi>=0.115.0,<1.0.0` - Kernel HTTP service
- `grpcio>=1.74.0,<2.0.0` - RPC communication
- `msgpack>=1.1.0,<2.0.0` - Serialization
- `openai>=1.52.0` / `httpx>=0.28.0` - absorbed middleware runtime operators

**Also owns now**: former `sage-middleware` runtime/operator responsibilities.

#### L3. sage-cli (Core user entrypoint)

**Core**:
- `typer>=0.15.0` - CLI framework
- `rich>=13.0.0` - Pretty output
- `click>=8.0.0` - Command parsing
- `jinja2>=3.1.0` - Templates
- `isage-dev-tools>=0.1.0` - Dev utilities

**Role**: top layer of the core workspace stack; applications should extend it rather than sit as
peers.

#### L4. Applications (`sage-studio`, benchmarks, docs-facing apps)

**Typical deps**:
- `isage>=...` - full framework integration
- `fastapi>=...` / frontend stacks - application API & UI
- app-specific packages such as `isagellm`, `isage-agentic`, `isage-neuromem`

**Note**: `sage-studio` is above `sage-cli`, not the same layer, because it plugs into the CLI via
the `sage.cli.plugins` entry-point surface.

### Capability Packages

Packages such as `isage-rag`, `isage-neuromem`, `isage-libs-intent`, and `isage-sias` remain
important capability dependencies, but they are no longer used as separate main-repo layer labels
in the workspace numbering.

### Feature Modules

When extras were removed, functionality migrated to independent packages:

| Feature | Before | Now |
|---------|--------|-----|
| Embedding | `commons[embedding]` | → `isage-neuromem` |
| Agentic | `libs[agentic]` | → `isage-agentic` |
| RAG | `libs[rag]` | → `isage-rag` |
| Evaluation | `libs[eval]` | → `isage-eval` |
| Vector DB | `middleware[vdb]` | → `isage-vdb` |
| Memory | `middleware[neuromem]` | → `isage-neuromem` |
| Streaming | `middleware[streaming]` | → `isage-flow` |

### Installation Examples

#### Minimal (core only)

```bash
pip install isage-common
pip install isage-platform       # Includes Flownet-aligned runtime integration
pip install isage-kernel isage-libs isage-middleware
````

#### Standard (recommended for most users)

```bash
pip install isage                # Meta package with all core layers
```

Then add features as needed:

```bash
pip install isage-agentic        # For agents
pip install isage-rag            # For RAG
pip install isage-vdb            # For vector search
pip install isagellm             # For LLM inference
```

#### Development (with all tools)

```bash
cd /path/to/SAGE
./quickstart.sh --dev --yes       # Installs core + dev tools + editable-first local deps
./quickstart.sh --standard --yes  # Installs core + dependencies from PyPI (stable path)
```

______________________________________________________________________

## Development Workflow

### Using the sage-dev CLI

The `sage-dev` CLI (provided by the independently released `isage-dev-tools` package) offers the
same development workflows:

> **💡 Note**: Additional development utilities are available via `sage-dev-tools` (automatically
> installed in `--dev` mode):
>
> - Work report generation: `sage-dev-tools report --period weekly`
> - Cluster code sync: `sage-dev-tools maintenance sync-cluster`
> - See: https://github.com/intellistream/sage-dev-tools

```bash
# Format code / auto-fix quality issues
sage-dev quality fix --all-files

# Run linters & quality checks
sage-dev quality check --check-only --all-files

# Run tests
sage-dev project test

# Run all checks before committing
sage-dev quality check --all-files --readme

# Clean build artifacts
sage-dev project clean --target all

# Clean build cache (egg-info, build, dist)
make clean-cache

# Or use the cache cleaner directly
bash tools/install/fixes/build_cache_cleaner.sh clean

# Build documentation
sage-dev docs build

# Get help
sage-dev --help
```

### Build Cache Management

SAGE includes automatic build cache detection and cleaning to prevent version inconsistencies:

**Automatic Cache Cleaning** (during installation):

- `quickstart.sh` automatically detects and cleans stale `egg-info` caches
- Checks for version mismatches between cached metadata and source code
- Only cleans caches when inconsistencies are detected

**Manual Cache Cleaning** (when needed):

```bash
# Clean all build caches (egg-info, build, dist)
make clean-cache

# Or use the cleaner tool directly
bash tools/install/fixes/build_cache_cleaner.sh clean

# Just detect and clean egg-info (automatic during install)
bash tools/install/fixes/build_cache_cleaner.sh detect
```

**When to clean cache manually:**

- After git pull if versions seem wrong
- Before reinstalling after version changes
- When `pip list` shows inconsistent versions

**Note:** The `quickstart.sh` script handles this automatically, so manual cleaning is rarely
needed.

### Development Tools Cache Configuration

SAGE centralizes all development tool caches in the `.sage/cache/` directory to keep the project
root clean. The following environment variables are configured in `.env`:

```bash
# Ruff cache directory (for linting)
RUFF_CACHE_DIR=.sage/cache/ruff

# Mypy cache directory (for type checking)
MYPY_CACHE_DIR=.sage/cache/mypy
```

**Pytest cache** is configured in `tools/config/pytest.ini`:

```ini
cache_dir = .sage/cache/pytest
```

**Why centralize caches?**

- ✅ Keeps project root directory clean
- ✅ Easy to clean all caches with `sage-dev project clean`
- ✅ Consistent location across all tools
- ✅ Follows SAGE architectural design (`.sage/` for project-level artifacts)

**To clean all caches:**

```bash
# Clean all temporary files and caches
sage-dev project clean --target all

# Clean only cache files
sage-dev project clean --target cache

# Preview what will be cleaned
sage-dev project clean --dry-run
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

## Code Quality

### Pre-commit Hooks Configuration

SAGE uses a **non-standard location** for pre-commit configuration:

- **Actual configuration**: `tools/pre-commit-config.yaml`
- **Standard location symlink**: `.pre-commit-config.yaml` → `tools/pre-commit-config.yaml`

**Why tools/ directory?**

- Centralized management with other dev tools (`sage-dev`, `maintenance/`)
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
sage-dev quality fix --all-files

# Or manually:
black packages/ scripts/ --line-length 100
isort packages/ scripts/ --profile black --line-length 100
```

**Configuration**:

- Line length: 100 characters
- isort profile: black (for compatibility)

### Linting

We use **Ruff** for fast linting and **mypy** for type checking:

```bash
# Run all linters
sage-dev quality check --check-only --all-files

# Or run individually:
ruff check packages/ scripts/
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
sage-dev project test

# Run unit tests only
sage-dev project test --test-type unit

# Run integration tests only
sage-dev project test --test-type integration

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
from sage.kernel.api.local_environment import LocalEnvironment


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
sage-dev docs build

# Serve documentation locally
sage-dev docs serve
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

1. **User Guides**: Place in `docs/`

1. **Changelog**: 重要变更统一记录到 `CHANGELOG.md`

### Updating Changelog

When documenting fixes or features:

```bash
# Edit repo changelog directly
$EDITOR CHANGELOG.md

# Add key changes under [Unreleased]
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
   sage-dev quality check --all-files --readme
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
   sage-dev quality check --all-files --readme
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

- **Documentation**: Check `docs/`, `README.md`, and `CONTRIBUTING.md`
- **Examples**: See [sage-examples](https://github.com/intellistream/sage-examples) repository
- **Issues**: Search existing issues or create new one
- **Community**: Join our
  [Slack](https://join.slack.com/t/intellistream/shared_invite/zt-2qayp8bs7-v4F71ge0RkO_rn34hBDWQg)
  or [WeChat](./docs/COMMUNITY.md)

## Useful Resources

- [Architecture Diagram](docs/images/architecture.svg)
- [Project Changelog](CHANGELOG.md)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

______________________________________________________________________

Thank you for contributing to SAGE! 🚀
