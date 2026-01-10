#!/bin/bash
# 创建 SAGE 独立算子库仓库
# 用法: ./create_sage_repos.sh

set -e

REPOS=(
    "sage-privacy:isage-privacy:Privacy protection, machine unlearning, differential privacy"
    "sage-finetune:isage-finetune:Model fine-tuning toolkit with LoRA, QLoRA, PEFT"
    "sage-eval:isage-eval:Evaluation metrics, profiling tools, and benchmarking"
    "sage-safety:isage-safety:Advanced safety guardrails and jailbreak detection"
)

HOME_DIR="/home/shuhao"
ORG="intellistream"

echo "🚀 创建 SAGE 独立仓库"
echo "===================="
echo ""

for repo_spec in "${REPOS[@]}"; do
    IFS=':' read -r repo_name pypi_name description <<< "$repo_spec"

    echo "📦 处理仓库: $repo_name"

    # 检查本地是否已存在
    if [ -d "$HOME_DIR/$repo_name" ]; then
        echo "  ⚠️  本地已存在: $HOME_DIR/$repo_name"
        cd "$HOME_DIR/$repo_name"

        # 检查远程仓库是否存在
        if gh repo view "$ORG/$repo_name" &>/dev/null; then
            echo "  ✅ 远程仓库已存在"
        else
            echo "  📤 创建远程仓库..."
            gh repo create "$ORG/$repo_name" \
                --private \
                --description "$description" \
                --source=. \
                --remote=origin \
                --push || true
        fi

        # 确保分支存在
        git checkout main 2>/dev/null || git checkout -b main
        git checkout main-dev 2>/dev/null || git checkout -b main-dev

        echo "  ✅ 分支已配置"
    else
        echo "  📥 创建新仓库..."

        # 检查远程仓库是否已存在
        if gh repo view "$ORG/$repo_name" &>/dev/null; then
            echo "  📥 克隆已存在的远程仓库..."
            gh repo clone "$ORG/$repo_name" "$HOME_DIR/$repo_name"
            cd "$HOME_DIR/$repo_name"
        else
            # 创建新仓库
            mkdir -p "$HOME_DIR/$repo_name"
            cd "$HOME_DIR/$repo_name"
            git init

            # 创建 README.md
            cat > README.md << EOF
# $repo_name

$description

**PyPI Package**: \`$pypi_name\`

## Installation

\`\`\`bash
pip install $pypi_name
\`\`\`

## Development

\`\`\`bash
git clone https://github.com/$ORG/$repo_name.git
cd $repo_name
pip install -e .[dev]
\`\`\`

## Usage

\`\`\`python
# Import from SAGE interface layer
from sage.libs.${repo_name#sage-}.interface import create, register

# Or import directly
import ${pypi_name//-/_}
\`\`\`

## License

Apache License 2.0
EOF

            # 创建 .gitignore
            cat > .gitignore << 'GITIGNORE'
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class
*.so

# Distribution / packaging
build/
dist/
*.egg-info/
.eggs/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Linting
.mypy_cache/
.ruff_cache/

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
GITIGNORE

            # 创建 pyproject.toml
            cat > pyproject.toml << PYPROJECT
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "$pypi_name"
version = "0.1.0"
description = "$description"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Apache-2.0"}
authors = [
    {name = "IntelliStream Team", email = "shuhao_zhang@hust.edu.cn"}
]
keywords = ["ai", "sage", "llm", "machine-learning"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "isage-libs>=0.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.8.0",
    "mypy>=1.0",
]

[project.urls]
Homepage = "https://github.com/$ORG/$repo_name"
Documentation = "https://sage.intellistream.com"
Repository = "https://github.com/$ORG/$repo_name"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "C4"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov"
PYPROJECT

            # 创建 src 目录结构
            pkg_name="${pypi_name//-/_}"
            mkdir -p "src/$pkg_name"

            cat > "src/$pkg_name/__init__.py" << INIT
"""$description

PyPI: $pypi_name
Repository: https://github.com/$ORG/$repo_name
"""

from ._version import __version__, __author__, __email__

__all__ = ["__version__", "__author__", "__email__"]
INIT

            cat > "src/$pkg_name/_version.py" << VERSION
"""Version information for $pypi_name."""
__version__ = "0.1.0"
__author__ = "IntelliStream Team"
__email__ = "shuhao_zhang@hust.edu.cn"
VERSION

            # 创建 tests 目录
            mkdir -p tests
            cat > tests/__init__.py << 'TESTINIT'
"""Tests for the package."""
TESTINIT

            cat > tests/test_version.py << TESTVERSION
"""Test version information."""

def test_version():
    from ${pkg_name} import __version__
    assert __version__ == "0.1.0"
TESTVERSION

            # 创建 CI/CD
            mkdir -p .github/workflows
            cat > .github/workflows/test.yml << 'WORKFLOW'
name: Test

on:
  push:
    branches: [main, main-dev]
  pull_request:
    branches: [main, main-dev]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e .[dev]

      - name: Run linters
        run: |
          ruff check .
          ruff format --check .

      - name: Run tests
        run: |
          pytest tests/ -v --cov
WORKFLOW

            # 初始提交
            git add .
            git commit -m "chore: initial commit for $repo_name"

            # 创建远程仓库
            echo "  📤 创建远程仓库..."
            gh repo create "$ORG/$repo_name" \
                --private \
                --description "$description" \
                --source=. \
                --remote=origin \
                --push
        fi

        # 确保分支存在
        git checkout main 2>/dev/null || git checkout -b main
        git push -u origin main 2>/dev/null || true

        git checkout -b main-dev 2>/dev/null || git checkout main-dev
        git push -u origin main-dev 2>/dev/null || true

        echo "  ✅ 仓库已创建并配置"
    fi

    echo ""
done

# 同步现有仓库分支
echo "🔄 同步现有仓库分支"
echo "===================="

EXISTING_REPOS=(
    "sage-agentic"
    "sage-amms"
    "sage-rag"
)

for repo_name in "${EXISTING_REPOS[@]}"; do
    if [ -d "$HOME_DIR/$repo_name" ]; then
        echo "📦 同步 $repo_name..."
        cd "$HOME_DIR/$repo_name"

        # 确保分支存在
        git fetch origin 2>/dev/null || true
        git checkout main 2>/dev/null || git checkout -b main
        git checkout main-dev 2>/dev/null || git checkout -b main-dev

        echo "  ✅ 分支已同步"
    else
        echo "  ⚠️  $repo_name 不存在"
    fi
done

echo ""
echo "✅ 所有仓库准备完成"
echo ""
echo "📋 仓库清单："
for repo_spec in "${REPOS[@]}"; do
    IFS=':' read -r repo_name pypi_name description <<< "$repo_spec"
    echo "  - $repo_name: https://github.com/$ORG/$repo_name"
done
echo ""
echo "🔗 现有仓库："
for repo_name in "${EXISTING_REPOS[@]}"; do
    echo "  - $repo_name: https://github.com/$ORG/$repo_name"
done
