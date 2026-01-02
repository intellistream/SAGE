# CI/CD Configuration

## Overview

SAGE uses GitHub Actions for continuous integration and deployment. This document provides a
comprehensive guide to the CI/CD pipeline, including workflows, environment setup, and best
practices.

## GitHub Actions Workflows

### Main Workflows

| Workflow              | File                    | Duration | Trigger          |
| --------------------- | ----------------------- | -------- | ---------------- |
| **Build & Test**      | `build-test.yml`        | ~45 min  | PR, Push to main |
| **Examples Test**     | `examples-test.yml`     | ~30 min  | PR, Push to main |
| **Code Quality**      | `code-quality.yml`      | ~10 min  | PR, Push to main |
| **Installation Test** | `installation-test.yml` | ~15 min  | PR, Push to main |
| **Publish PyPI**      | `publish-pypi.yml`      | ~10 min  | Release tag      |

### CI Environment

- **OS**: Ubuntu latest
- **Python**: 3.11 (primary), 3.10+ supported
- **Cache**: pip cache enabled for faster builds

### CI 安装矩阵

| 场景                           | 建议命令                                                                                    | 说明                                                                                       |
| ------------------------------ | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| GitHub Actions (ubuntu-latest) | `./tools/install/ci_install_wrapper.sh --dev --yes`                                         | 包装脚本会自动安装构建依赖并缓存到 `~/.local`; 适合默认托管 Runner                         |
| GitHub Actions + Conda         | `unset CI GITHUB_ACTIONS && ./quickstart.sh --dev --yes --pip`                              | `quickstart.sh` 在检测到 `CI=true` 时会强制 `--user`，需先取消变量使其安装到当前 Conda env |
| 自建 GPU Runner（境内）        | `unset CI GITHUB_ACTIONS && SAGE_FORCE_CHINA_MIRROR=true ./quickstart.sh --dev --yes --pip` | `SAGE_FORCE_CHINA_MIRROR=true` 让脚本切换至清华 PyPI + hf-mirror，解决模型下载限速         |

**为什么需要 `unset CI GITHUB_ACTIONS`？**

- `quickstart.sh`（仓库根目录）在检测到 CI 环境变量时会附加 `--user`，默认将包装入 `~/.local`。
- 若 CI 中预先创建了 Conda/virtualenv，我们希望安装到该环境而非 `~/.local`，因此在执行安装前需要显式清除 `CI` 与 `GITHUB_ACTIONS`。

**为什么需要 `SAGE_FORCE_CHINA_MIRROR=true`？**

- 执行脚本时会触发 `sage.common.config.network.ensure_hf_mirror_configured()`，该变量可强制切换为中国大陆镜像（清华 PyPI +
  `https://hf-mirror.com`）。
- 适用于自建 Runner/高校服务器，避免 HuggingFace / PyPI 下载失败。

相关脚本：

- `tools/install/ci_install_wrapper.sh`：统一入口（用于 GH Actions matrix jobs）。
- `quickstart.sh`：安装核心逻辑，负责选择 `--core/--standard/--full/--dev` 模式。
- `tools/install/check_tool_versions.sh`：CI 安装完成后运行 `sage-dev quality` 前确保 `ruff` 版本在
  `tools/pre-commit-config.yaml` 与 `packages/sage-tools/pyproject.toml` 间保持一致。

### Required Secrets

Configure these in GitHub repository settings:

```yaml
OPENAI_API_KEY    # For LLM-based tests
HF_TOKEN          # For HuggingFace model downloads
CODECOV_TOKEN     # For coverage reporting
PYPI_API_TOKEN    # For package publishing
```

## Local CI Replication

### Quick Start

```bash
# 1. Full development install
./quickstart.sh --dev --yes

# 2. Run tests with coverage (same as CI)
sage-dev project test --coverage --jobs 4 --timeout 300

# 3. Run code quality checks
pre-commit run --all-files --config tools/pre-commit-config.yaml

# 4. Build documentation
cd docs-public && mkdocs build --strict
```

### Pre-commit Hooks

Install hooks to run checks automatically before commits:

```bash
# Install hooks
pre-commit install --config tools/pre-commit-config.yaml

# Run manually
pre-commit run --all-files --config tools/pre-commit-config.yaml

# Update hooks
pre-commit autoupdate
```

**Hooks included**:

- **Python Formatting**: Ruff formatter (line-length=100)
- **Python Linting**: Ruff linter with type hints
- **Type Checking**: Mypy (warning mode)
- **Shell Scripts**: Shellcheck
- **General**: Trailing whitespace, YAML/JSON validation
- **Security**: detect-secrets

## Submodule Management

SAGE uses git submodules for C++ extensions in
`packages/sage-middleware/src/sage/middleware/components/`.

### Critical Rules

!!! warning "重要" **NEVER** use `git submodule update --init` directly. Always use the provided
tools.

### Submodule Commands

```bash
# Bootstrap (first time setup)
./manage.sh

# Initialize submodules
./tools/maintenance/sage-maintenance.sh submodule init

# Fix detached HEAD
./tools/maintenance/sage-maintenance.sh submodule switch

# Update submodules
./tools/maintenance/sage-maintenance.sh submodule update

# Cleanup
./tools/maintenance/sage-maintenance.sh submodule cleanup
```

Or via `sage-dev`:

```bash
sage-dev maintain submodule init
sage-dev maintain submodule status
sage-dev maintain submodule switch
sage-dev maintain submodule update
```

## Code Coverage

### CodeCov Integration

Coverage is collected during CI and reported to CodeCov:

```bash
# Run tests with coverage
sage-dev project test --coverage

# View local HTML report
open htmlcov/index.html
```

### Coverage Configuration

- Config: `tools/pytest.ini`
- Cache: `.sage/cache/pytest/`
- Reports: `htmlcov/`, `coverage.xml`, `coverage.json`

### Coverage Targets

| Package         | Target | Status |
| --------------- | ------ | ------ |
| sage-common     | 80%    | ✅     |
| sage-kernel     | 70%    | ✅     |
| sage-libs       | 60%    | 🔄     |
| sage-middleware | 50%    | 🔄     |

## Testing Guidelines

### Test Categories

```python
# Unit tests - fast, isolated
@pytest.mark.unit
def test_something():
    pass

# Integration tests - slower, real dependencies
@pytest.mark.integration
def test_integration():
    pass

# Slow tests - skip in quick mode
@pytest.mark.slow
def test_slow_operation():
    pass
```

### Running Tests

```bash
# All tests
sage-dev project test

# Quick tests (skip slow)
sage-dev project test --quick

# Specific package
pytest packages/sage-kernel/tests/unit/ -v

# With verbose output
sage-dev project test --verbose

# With coverage
sage-dev project test --coverage
```

### Environment Variables

```bash
export SAGE_TEST_MODE=true      # Enable test mode
export SAGE_LOG_LEVEL=DEBUG     # Verbose logging
export PYTEST_TIMEOUT=300       # Test timeout (seconds)
```

## Quality Checks

### Code Quality Commands

```bash
# Run all quality checks
sage-dev quality check

# Check only (no auto-fix)
sage-dev quality check --check-only

# Auto-fix issues
sage-dev quality fix

# Architecture compliance
sage-dev quality architecture --changed-only

# README quality
sage-dev quality readme
```

### Code Style Standards

- **Line Length**: 100 characters
- **Formatter**: Ruff format (compatible with Black)
- **Import Sorting**: Ruff isort (Black profile)
- **Linter**: Ruff
- **Type Checking**: Mypy (warning mode)

### Configuration Files

| Tool       | Config File                    |
| ---------- | ------------------------------ |
| Ruff       | `tools/ruff.toml`              |
| Pytest     | `tools/pytest.ini`             |
| Pre-commit | `tools/pre-commit-config.yaml` |
| Mypy       | `pyproject.toml`               |

## CI Debugging

### Common Issues

1. **Submodule build fails**

   ```bash
   ./tools/maintenance/sage-maintenance.sh submodule init
   ```

1. **C++ compilation errors**

   ```bash
   # Ensure dependencies installed
   sudo apt install build-essential cmake pkg-config libopenblas-dev liblapack-dev
   ```

1. **API key issues**

   - Check GitHub Secrets configuration
   - Verify `.env` file locally

1. **Test timeout**

   ```bash
   sage-dev project test --timeout 600
   ```

### Debug Workflow

```bash
# 1. Check CI logs in GitHub Actions
# 2. Identify failed step

# 3. Run locally
sage-dev project test --coverage --verbose

# 4. If submodule issue
sage-dev maintain submodule status

# 5. If build issue
rm -rf .sage/build/ build/ dist/
./quickstart.sh --dev --yes
```

## Release Process

### Version Management

```bash
# View current versions
sage-dev package version list

# Bump version
sage-dev package version bump patch  # 0.1.5 -> 0.1.6
sage-dev package version bump minor  # 0.1.5 -> 0.2.0
sage-dev package version bump major  # 0.1.5 -> 1.0.0

# Sync all package versions
sage-dev package version sync
```

### Release Checklist

1. [ ] All tests passing
1. [ ] Coverage targets met
1. [ ] CHANGELOG.md updated
1. [ ] Version bumped
1. [ ] Documentation updated
1. [ ] PR approved and merged
1. [ ] Git tag created
1. [ ] PyPI release triggered

### Publishing

```bash
# Validate package
sage-dev package pypi validate

# Build distribution
sage-dev package pypi build

# Publish to TestPyPI (dry run)
sage-dev package pypi publish --dry-run

# Publish to production PyPI
sage-dev package pypi publish
```

## Related Documentation

- [GitHub Workflows](https://github.com/intellistream/SAGE/tree/main/.github/workflows) - CI/CD
  workflow definitions
- [Development Setup](./development-setup.md) - Local development environment
- [CLI Commands](./commands.md) - Complete command reference
- [Internal Dev Notes](https://github.com/intellistream/SAGE/tree/main/docs/dev-notes/cross-layer/ci-cd)
  \- Detailed CI/CD notes
