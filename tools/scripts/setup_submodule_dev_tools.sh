#!/bin/bash
# Setup development tools (pre-commit, pytest) for submodules
# This script creates standardized configuration files for each submodule

set -euo pipefail

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║       🔧 为子模块设置开发工具 (pre-commit + pytest)                        ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Define submodules with their types
declare -A SUBMODULES=(
    ["packages/sage-llm-core/src/sage/llm/sageLLM"]="python"
    # 注意: C++ 扩展已迁移为独立 PyPI 包，不再作为子模块
    # - isagedb (was sageDB)
    # - isage-flow (was sageFlow)
    # - isage-tsdb (was sageTSDB)
    # - neuromem
    # - isage-refiner (was sageRefiner)
    # 只保留实际的 Git 子模块
)

# Function to create pre-commit config for C++ projects
create_cpp_precommit() {
    local target_dir="$1"
    local submodule_name=$(basename "$target_dir")

    cat > "$target_dir/.pre-commit-config.yaml" << 'EOF'
# Pre-commit hooks configuration for C++ submodule
# Installation:
#   pip install pre-commit
#   pre-commit install
#
# Usage:
#   pre-commit run --all-files
#   git commit --no-verify  # Skip hooks temporarily

default_language_version:
  python: python3.11

repos:
  # General file checks
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v6.0.0
  hooks:
  - id: trailing-whitespace
  - id: end-of-file-fixer
  - id: check-yaml
    args: [--unsafe]
  - id: check-json
  - id: check-toml
  - id: check-added-large-files
    args: ['--maxkb=1000']
  - id: check-merge-conflict
  - id: check-case-conflict
  - id: mixed-line-ending
    args: [--fix=lf]
  - id: detect-private-key

  # C++: clang-format (code formatting)
- repo: https://github.com/pre-commit/mirrors-clang-format
  rev: v19.1.6
  hooks:
  - id: clang-format
    types_or: [c++, c]
    args: ['-i']

  # CMake: cmake-format
- repo: https://github.com/cheshirekow/cmake-format-precommit
  rev: v0.6.13
  hooks:
  - id: cmake-format
    args: [--in-place]
  - id: cmake-lint
    args: [--disabled-codes=C0103,C0301]

  # Python (for pybind11 bindings and test scripts)
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.14.2
  hooks:
  - id: ruff
    args: [--fix]
    types_or: [python, pyi]
  - id: ruff-format
    types_or: [python, pyi]

  # Shell scripts
- repo: https://github.com/shellcheck-py/shellcheck-py
  rev: v0.10.0.1
  hooks:
  - id: shellcheck
    args: [--severity=warning]

  # YAML formatting
- repo: https://github.com/macisamuele/language-formatters-pre-commit-hooks
  rev: v2.15.0
  hooks:
  - id: pretty-format-yaml
    args: [--autofix, --indent, '2']

  # Markdown formatting
- repo: https://github.com/executablebooks/mdformat
  rev: 0.7.21
  hooks:
  - id: mdformat
    args: [--wrap, '100']
    additional_dependencies:
    - mdformat-gfm
    - mdformat-black

  # Secret detection
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.5.0
  hooks:
  - id: detect-secrets
    args: ['--baseline', '.secrets.baseline']
    exclude: package.lock.json
EOF

    echo "✅ Created .pre-commit-config.yaml for $submodule_name (C++)"
}

# Function to create pre-commit config for Python projects
create_python_precommit() {
    local target_dir="$1"
    local submodule_name=$(basename "$target_dir")

    cat > "$target_dir/.pre-commit-config.yaml" << 'EOF'
# Pre-commit hooks configuration for Python submodule
# Installation:
#   pip install pre-commit
#   pre-commit install
#
# Usage:
#   pre-commit run --all-files
#   git commit --no-verify  # Skip hooks temporarily

default_language_version:
  python: python3.11

repos:
  # General file checks
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v6.0.0
  hooks:
  - id: trailing-whitespace
    args: [--markdown-linebreak-ext=md]
  - id: end-of-file-fixer
  - id: check-yaml
    args: [--unsafe]
  - id: check-json
  - id: check-toml
  - id: check-added-large-files
    args: ['--maxkb=1000']
  - id: check-merge-conflict
  - id: check-case-conflict
  - id: mixed-line-ending
    args: [--fix=lf]
  - id: detect-private-key

  # Python: Ruff linter and formatter
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.14.2
  hooks:
  - id: ruff
    args: [--fix]
    types_or: [python, pyi]
  - id: ruff-format
    types_or: [python, pyi]

  # Python: mypy type checking
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.14.0
  hooks:
  - id: mypy
    args: [--config-file=pyproject.toml, --no-error-summary]
    additional_dependencies:
    - types-PyYAML
    - types-requests
    - types-setuptools

  # Shell scripts
- repo: https://github.com/shellcheck-py/shellcheck-py
  rev: v0.10.0.1
  hooks:
  - id: shellcheck
    args: [--severity=warning]

  # YAML formatting
- repo: https://github.com/macisamuele/language-formatters-pre-commit-hooks
  rev: v2.15.0
  hooks:
  - id: pretty-format-yaml
    args: [--autofix, --indent, '2']

  # Markdown formatting
- repo: https://github.com/executablebooks/mdformat
  rev: 0.7.21
  hooks:
  - id: mdformat
    args: [--wrap, '100']
    additional_dependencies:
    - mdformat-gfm
    - mdformat-black

  # Secret detection
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.5.0
  hooks:
  - id: detect-secrets
    args: ['--baseline', '.secrets.baseline']
    exclude: package.lock.json
EOF

    echo "✅ Created .pre-commit-config.yaml for $submodule_name (Python)"
}

# Function to create pytest.ini
create_pytest_ini() {
    local target_dir="$1"
    local submodule_name=$(basename "$target_dir")

    cat > "$target_dir/pytest.ini" << 'EOF'
[pytest]
# pytest configuration for submodule

# Test discovery patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Add markers for async tests
asyncio_mode = auto

# Logging
log_cli = true
log_cli_level = INFO
log_file = pytest.log
log_file_level = DEBUG

# Output options
addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings
    --cov=.
    --cov-report=term-missing
    --cov-report=html:htmlcov

# Test paths
testpaths =
    tests

# Markers for test categorization
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests (use -m "not slow" to skip)
    gpu: Tests requiring GPU
    cpp: Tests for C++ bindings

# Ignore certain paths
norecursedirs =
    .git
    .tox
    dist
    build
    *.egg
    vendors
    third_party
EOF

    echo "✅ Created pytest.ini for $submodule_name"
}

# Main execution
echo "📋 检查子模块并创建缺失的配置文件..."
echo ""

for submodule_path in "${!SUBMODULES[@]}"; do
    submodule_type="${SUBMODULES[$submodule_path]}"
    submodule_name=$(basename "$submodule_path")

    if [ ! -d "$submodule_path" ]; then
        echo "⚠️  跳过: $submodule_name (目录不存在)"
        continue
    fi

    echo "📦 处理: $submodule_name ($submodule_type)"

    # Create pre-commit config if missing
    if [ ! -f "$submodule_path/.pre-commit-config.yaml" ]; then
        if [ "$submodule_type" == "cpp" ]; then
            create_cpp_precommit "$submodule_path"
        else
            create_python_precommit "$submodule_path"
        fi
    else
        echo "   ⏭️  .pre-commit-config.yaml 已存在"
    fi

    # Create pytest.ini if missing
    if [ ! -f "$submodule_path/pytest.ini" ]; then
        create_pytest_ini "$submodule_path"
    else
        echo "   ⏭️  pytest.ini 已存在"
    fi

    echo ""
done

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                          ✅ 配置文件创建完成                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 下一步操作："
echo ""
echo "1. 进入每个子模块目录"
echo "2. 运行: pre-commit install"
echo "3. 运行: pre-commit run --all-files"
echo "4. 提交配置文件到子模块仓库"
echo ""
echo "示例命令："
echo "  cd packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB"
echo "  pre-commit install"
echo "  pre-commit run --all-files"
echo "  git add .pre-commit-config.yaml pytest.ini"
echo "  git commit -m 'chore: add pre-commit and pytest configuration'"
echo ""
