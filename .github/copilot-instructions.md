# SAGE Copilot Instructions

## Repository Overview

**SAGE (Streaming-Augmented Generative Execution)** is a high-performance Python framework for building AI-powered data processing pipelines with declarative dataflow abstractions. The repository uses a modular, multi-layered architecture with 10 functional packages plus a meta-package.

- **Language**: Python 3.10+ (tested on 3.10, 3.11, 3.12)
- **Size**: ~400MB (dev install), 11 package directories (10 functional + 1 meta), ~500+ Python files
- **Framework**: Declarative dataflow architecture for LLM/AI pipelines
- **Key Technologies**: Python, C++ extensions (CMake), pytest, GitHub Actions

## Package Architecture (L1-L6 Layers)

**Critical**: Maintain strict unidirectional dependencies (no upward dependencies).

```
L6: sage-cli, sage-studio, sage-tools      # User Interfaces & Dev Tools
L5: sage-apps, sage-benchmark               # Applications & Benchmarks  
L4: sage-middleware                         # Domain Operators (has C++ extensions)
L3: sage-kernel, sage-libs                  # Core Engine & Algorithms
L2: sage-platform                           # Platform Services
L1: sage-common                             # Foundation & Utilities
```

**Package Locations**: All packages in `/packages/<package-name>/` (10 functional packages + 1 meta-package `sage`)

**Architecture Rules**:
- L6 can import from L1-L5
- L5 can import from L1-L4
- L4 can import from L1-L3
- Never import from higher layers

## Installation & Environment Setup

### Prerequisites

- Python 3.10+ (3.11 recommended for CI)
- Git with submodule support
- Build tools: `build-essential`, `cmake`, `pkg-config` (for C++ extensions)
- System libs: `libopenblas-dev`, `liblapack-dev` (for C++ extensions)

### Installation Commands

**ALWAYS use these exact commands for installation**:

```bash
# Core installation (production use - no C++ extensions)
./quickstart.sh --core --yes

# Standard installation (includes CLI, most features)
./quickstart.sh --standard --yes

# Full installation (includes apps, benchmarks)
./quickstart.sh --full --yes

# Developer installation (REQUIRED for development work)
./quickstart.sh --dev --yes

# With vLLM support (if needed)
./quickstart.sh --dev --vllm --yes
```

**Environment Options**:
- `--pip`: Use current Python environment
- `--conda`: Create conda environment (auto-selected if not in venv)
- `--yes` or `--y`: Skip confirmation prompts (always use in CI/automation)
- `--no-sync-submodules`: Skip automatic submodule sync (use when submodules already initialized)

**Installation takes 10-25 minutes** depending on mode and network speed.

### Submodule Management

**CRITICAL**: NEVER use `git submodule update --init` directly (causes detached HEAD).

**ALWAYS use the maintenance tool**:

```bash
# Initialize submodules (first time or after clone)
./tools/maintenance/sage-maintenance.sh submodule init

# Or use the wrapper
./manage.sh

# Check submodule status
./tools/maintenance/sage-maintenance.sh submodule status

# Switch submodule branches (after switching SAGE branch)
./tools/maintenance/sage-maintenance.sh submodule switch

# Fix conflicts
./tools/maintenance/sage-maintenance.sh submodule fix-conflict
```

**Submodules** (C++ extensions in sage-middleware):
- `packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB`
- `packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow`
- `packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB`
- `packages/sage-common/src/sage/common/components/sage_vllm/sageLLM`

### Environment Configuration

After installation, create `.env` file for API keys:

```bash
# Copy template
cp .env.template .env

# Or use interactive setup
python -m sage.tools.cli.main config env setup
```

**Required API keys** for running examples/tests:
- `OPENAI_API_KEY` - For GPT models and most LLM examples
- `HF_TOKEN` - For Hugging Face model downloads

## Build & Development Workflow

### Build Commands

**Development mode (editable install)**:
```bash
# Install in development mode (creates .egg-info in source tree)
./quickstart.sh --dev --yes

# Build C++ extensions (happens automatically during dev install)
# Extensions are built in .sage/build/ directory
```

**C++ Extensions**:
- Built automatically during `--dev` or `--full` installation
- Requires submodules to be initialized first
- Build artifacts in `.sage/build/` (gitignored)
- If build fails, installation continues but extensions won't be available
- Check extension status: `python -c "from sage.middleware.components.extensions_compat import check_extensions_availability; print(check_extensions_availability())"`

### Testing

**ALWAYS run tests using sage-dev CLI (not direct pytest)**:

```bash
# Run all tests with coverage
sage-dev project test --coverage

# Run quick tests only (excludes slow tests)
sage-dev project test --quick

# Run specific test file
pytest packages/sage-kernel/tests/unit/test_specific.py -v

# Run examples tests
sage-dev examples test

# Old shell script (deprecated but still works)
bash tools/tests/run_examples_tests.sh
```

**Test Configuration**:
- Test files: `test_*.py` in `packages/*/tests/`
- pytest config: `tools/pytest.ini` (used by all packages)
- Cache dir: `.sage/cache/pytest/`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Do not run pytest from package directories** - always run from repo root

**Test Environment Variables**:
- `SAGE_TEST_MODE=true` - Enable test mode (uses mocks)
- `SAGE_EXAMPLES_MODE=test` - Run examples in test mode
- `CI=true` - CI environment detection

### Linting & Code Quality

**ALWAYS use pre-commit or sage-dev commands**:

```bash
# Format code (ruff format + ruff check --fix)
sage-dev quality

# Check code quality without fixing
sage-dev quality --check-only

# Run pre-commit hooks manually
pre-commit run --all-files --config tools/pre-commit-config.yaml

# Install pre-commit hooks (done automatically by quickstart.sh --dev)
pre-commit install --config tools/pre-commit-config.yaml
```

**Code Quality Tools**:
- **Ruff**: Linting and formatting (replaces black, isort, flake8)
- **Mypy**: Type checking (warning mode, doesn't block commits)
- **Shellcheck**: Shell script validation
- **detect-secrets**: Prevent secrets in commits

**Configuration Files**:
- Pre-commit: `tools/pre-commit-config.yaml` (symlinked to `.pre-commit-config.yaml`)
- Ruff: `tools/ruff.toml`
- Mypy: Uses `--cache-dir=.sage/cache/mypy`

**Formatting Standards**:
- Line length: 100 characters
- Python 3.10+ syntax
- Type hints encouraged but not required

### Common Development Commands

```bash
# Show all available commands
make help

# Format code
make format

# Run linting
make lint

# Run all tests
make test

# Build documentation
make docs

# Clean build artifacts
make clean

# Show version
make version
```

**Alternative using dev.sh (being migrated to sage-dev)**:
```bash
./tools/dev.sh help
./tools/dev.sh validate  # Run all checks
```

## GitHub Actions CI/CD

### Workflow Files (`.github/workflows/`)

**Main Workflows**:
1. **build-test.yml** - Build, test, and coverage (runs on push/PR to main/main-dev)
2. **examples-test.yml** - Test examples (runs when examples/ or packages/ change)
3. **code-quality.yml** - Code quality checks (runs on Python file changes)
4. **pip-installation-test.yml** - Test pip installation methods
5. **publish-pypi.yml** - Publish to PyPI (manual trigger)

**CI Timeout**: 45 minutes (build-test), 30 minutes (examples-test)

**CI Environment**:
- Ubuntu latest
- Python 3.11
- Uses GitHub Secrets for API keys (OPENAI_API_KEY, HF_TOKEN, etc.)
- Caches pip packages for speed

### Running CI Locally

**To replicate CI environment**:

```bash
# Install with same mode as CI
./quickstart.sh --dev --yes

# Run tests same as CI
sage-dev project test --coverage \
  --coverage-report term,xml,html \
  --jobs 4 \
  --timeout 300

# Run code quality checks same as CI  
pre-commit run --all-files --config tools/pre-commit-config.yaml
```

### CI Debugging Tips

**If CI fails**:
1. Check the specific job logs in GitHub Actions
2. Look for C++ extension build failures in "Verify C++ Extensions" step
3. Check if submodules were initialized properly
4. Verify API keys are set (for examples-test)
5. Run locally: `sage-dev project test --coverage`

**Common CI Issues**:
- **Submodules not initialized**: Check "Verify Submodules" step
- **C++ extensions build failed**: May continue but mark as unavailable
- **Tests timeout**: Default 300s per test, check for hanging tests
- **Code quality fails**: Run `pre-commit run --all-files` locally first

## File Structure & Key Locations

### Root Directory
```
.github/              # CI/CD workflows and issue templates
  workflows/          # GitHub Actions workflow definitions
  copilot-instructions.md  # This file
docs/                 # Developer documentation and dev-notes
docs-public/          # User-facing documentation (submodule)
examples/             # Example applications and tutorials
  apps/               # Full example applications
  tutorials/          # Tutorial examples organized by layer
packages/             # All 10 SAGE packages (L1-L6)
tools/                # Development tools and scripts
  dev.sh              # Developer helper script (migrating to sage-dev)
  maintenance/        # Maintenance utilities (submodules, hooks, etc.)
  install/            # Installation utilities
  pytest.ini          # pytest configuration
  pre-commit-config.yaml  # Pre-commit hooks configuration
  ruff.toml           # Ruff linter/formatter configuration
.env.template         # Template for environment variables
.gitignore            # Git ignore patterns
.pre-commit-config.yaml  # Symlink to tools/pre-commit-config.yaml
codecov.yml           # Code coverage configuration
manage.sh             # Wrapper for submodule management
quickstart.sh         # Main installation script
Makefile              # Developer shortcuts
README.md             # User-facing README
CONTRIBUTING.md       # Contribution guidelines (Chinese + English)
DEVELOPER.md          # Developer guide (English)
```

### Package Structure (each package follows this)
```
packages/<package-name>/
  src/
    sage/<module>/    # Source code
  tests/
    unit/             # Unit tests
    integration/      # Integration tests
  setup.py            # Setup script
  pyproject.toml      # Package configuration
  README.md           # Package documentation
```

### Build & Cache Directories (gitignored)
```
.sage/                # SAGE working directory
  build/              # C++ extension build artifacts
  cache/              # pytest, mypy, pip cache
  logs/               # Installation and runtime logs
  tmp/                # Temporary files
  coverage/           # Coverage reports
build/                # Legacy build directory (deprecated)
dist/                 # Distribution packages
*.egg-info/           # Package metadata
```

## Common Pitfalls & Solutions

### Installation Issues

**Problem**: Installation hangs or takes very long
- **Solution**: Check network connection, try `--no-cache-clean` flag
- **Timeout**: Normal installation takes 10-25 minutes

**Problem**: C++ extensions fail to build
- **Solution**: Ensure system dependencies installed: `sudo apt-get install build-essential cmake pkg-config libopenblas-dev liblapack-dev`
- **Note**: Installation continues even if extensions fail, but functionality limited

**Problem**: Submodule in detached HEAD state
- **Solution**: Never use `git submodule update --init`, use `./tools/maintenance/sage-maintenance.sh submodule switch`

### Testing Issues

**Problem**: Tests pass locally but fail in CI
- **Solution**: Always run with sage-dev CLI: `sage-dev project test --coverage`
- **Check**: Environment variables (SAGE_TEST_MODE, CI)

**Problem**: Import errors when running tests
- **Solution**: Run pytest from repository root, not from package directory
- **Check**: Installation mode (must be `--dev` for development)

**Problem**: C++ extension import failures in tests
- **Solution**: Check if extensions built successfully, verify with `sage-dev project test`
- **Note**: Some tests may skip if extensions unavailable

### Code Quality Issues

**Problem**: Pre-commit hooks fail on commit
- **Solution**: Run `sage-dev quality` to auto-fix most issues
- **Manual**: `ruff check --fix .` and `ruff format .`

**Problem**: Mypy type errors
- **Note**: Mypy runs in warning mode, doesn't block commits
- **Fix**: Address type hints if modifying the code

**Problem**: Architecture compliance check fails
- **Solution**: Check that imports follow layer rules (no upward dependencies)
- **Command**: `sage-dev quality architecture`

### Build Issues

**Problem**: Old build artifacts cause issues
- **Solution**: `make clean` or `rm -rf .sage/build/ build/ dist/ *.egg-info/`

**Problem**: Package version mismatches
- **Solution**: Reinstall in development mode: `./quickstart.sh --dev --yes`

## Best Practices for Code Changes

### Before Making Changes

1. **Install in development mode**: `./quickstart.sh --dev --yes`
2. **Initialize submodules**: `./manage.sh` (if working with C++ extensions)
3. **Verify installation**: `sage-dev project status` or `python -c "import sage; print(sage.__version__)"`

### During Development

1. **Run tests frequently**: `sage-dev project test` or `pytest packages/sage-<package>/tests/ -v`
2. **Format code**: `sage-dev quality` or let pre-commit hooks auto-format
3. **Check architecture**: Ensure no upward layer dependencies
4. **Update tests**: Add tests for new functionality

### Before Committing

1. **Run full validation**: `sage-dev quality --check-only`
2. **Run tests**: `sage-dev project test --coverage`
3. **Check examples**: `sage-dev examples test` (if examples changed)
4. **Update documentation**: Update README, docstrings, dev-notes as needed

### Commit Message Format

Follow conventional commits (enforced by pre-commit):

```
<type>(<scope>): <summary>

<body - optional>

<footer - optional>
```

**Types**: feat, fix, refactor, docs, test, style, perf, ci, chore, build, deps, revert, security

**Scopes**: sage-common, sage-kernel, sage-libs, sage-middleware, sage-tools, ci, docs, etc.

**Examples**:
- `feat(sage-kernel): add pipeline builder support for custom operators`
- `fix(ci): resolve submodule initialization in GitHub Actions`
- `docs(sage-libs): update RAG integration examples`

### PR Guidelines

1. **Run CI checks locally first**: `pre-commit run --all-files`
2. **Ensure tests pass**: `sage-dev project test --coverage`
3. **Check examples**: `sage-dev examples test` (if examples affected)
4. **Update CHANGELOG.md**: Add entry under "Unreleased" section
5. **Reference issues**: Use `Closes #<issue-number>` in commit/PR description

## Critical Files - Do Not Modify Without Review

- `quickstart.sh` - Main installation entry point
- `tools/maintenance/sage-maintenance.sh` - Submodule management
- `.github/workflows/*.yml` - CI/CD workflows
- `tools/pytest.ini` - Test configuration
- `tools/pre-commit-config.yaml` - Code quality hooks
- Package `setup.py` and `pyproject.toml` - Package configuration

## Additional Resources

- **Architecture Guide**: `docs-public/docs_src/dev-notes/package-architecture.md`
- **Contribution Guide**: `CONTRIBUTING.md` (Chinese), `DEVELOPER.md` (English)
- **Dev Notes**: `docs/dev-notes/` - Organized by layer (l1-l6, cross-layer)
- **CI/CD Docs**: `docs/dev-notes/cross-layer/ci-cd/`
- **Community**: Slack, WeChat, QQ (see `docs/COMMUNITY.md`)

## Trust These Instructions

**These instructions are comprehensive and tested.** Only search for additional information if:
- Instructions are incomplete for your specific task
- You encounter errors not documented here
- You need deeper architectural understanding

For most development tasks, following these instructions will minimize exploration time and prevent common mistakes.
