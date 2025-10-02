# Developer Guide

Welcome to the SAGE development guide! This document will help you get started with contributing to SAGE.

## Table of Contents

- [Development Setup](#development-setup)
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

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/intellistream/SAGE.git
   cd SAGE
   ```

2. **Run the developer setup script**
   ```bash
   ./scripts/dev.sh setup
   ```
   
   This will:
   - Install pre-commit hooks
   - Install SAGE in development mode
   - Install all development dependencies

3. **Verify the setup**
   ```bash
   ./scripts/dev.sh validate
   ```

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
./scripts/dev.sh format

# Run linters
./scripts/dev.sh lint

# Run tests
./scripts/dev.sh test

# Run all checks before committing
./scripts/dev.sh validate

# Clean build artifacts
./scripts/dev.sh clean

# Build documentation
./scripts/dev.sh docs

# Get help
./scripts/dev.sh help
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

### Code Formatting

We use **Black** and **isort** for consistent code formatting:

```bash
# Format all code
./scripts/dev.sh format

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
./scripts/dev.sh lint

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
./scripts/dev.sh test

# Run unit tests only
./scripts/dev.sh test-unit

# Run integration tests only
./scripts/dev.sh test-integration

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
./scripts/dev.sh docs

# Serve documentation locally
./scripts/dev.sh serve-docs
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

2. **User Guides**: Place in `docs-public/docs_src/`
3. **Dev Notes**: Use the template in `docs/dev-notes/TEMPLATE.md`

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

2. **Update version numbers**
   - Update version in `setup.py` or `pyproject.toml`
   - Update version in `__init__.py` files

3. **Run validation**
   ```bash
   ./scripts/dev.sh validate
   ```

4. **Create git tag**
   ```bash
   git tag -a v0.2.0 -m "Release version 0.2.0"
   git push origin v0.2.0
   ```

5. **Create GitHub release**
   - Go to GitHub releases page
   - Create new release from tag
   - Copy CHANGELOG entry to release notes

6. **Publish to PyPI** (maintainers only)
   ```bash
   python -m build
   python -m twine upload dist/*
   ```

## Contributing Guidelines

### Before Starting

1. Check existing issues and PRs to avoid duplicates
2. For large changes, open an issue first to discuss
3. Read `CONTRIBUTING.md` for detailed guidelines

### Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-feature
   # or
   git checkout -b fix/issue-123
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Run validation**
   ```bash
   ./scripts/dev.sh validate
   ```

4. **Commit your changes**
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

5. **Push and create PR**
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
- **Community**: Join our [Slack](https://join.slack.com/t/intellistream/shared_invite/zt-2qayp8bs7-v4F71ge0RkO_rn34hBDWQg) or [WeChat](./docs/COMMUNITY.md)

## Useful Resources

- [Architecture Diagram](docs/images/architecture.svg)
- [Dev Notes Template](docs/dev-notes/TEMPLATE.md)
- [Dev Notes Quick Start](docs/dev-notes/QUICK_START.md)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

---

Thank you for contributing to SAGE! 🚀
