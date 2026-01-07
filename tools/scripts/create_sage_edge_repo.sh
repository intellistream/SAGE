#!/usr/bin/env bash
# Create sage-edge independent repository with GitHub CLI
# Usage: ./create_sage_edge_repo.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}ℹ ${NC}$1"; }
echo_success() { echo -e "${GREEN}✓${NC} $1"; }
echo_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
echo_error() { echo -e "${RED}✗${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."

    if ! command -v gh &> /dev/null; then
        echo_error "GitHub CLI (gh) not found. Install it first:"
        echo "  macOS: brew install gh"
        echo "  Ubuntu: sudo apt install gh"
        echo "  See: https://cli.github.com/manual/installation"
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        echo_warning "Not authenticated with GitHub."

        # Try to authenticate from .env file
        if [ -f "$SAGE_REPO/.env" ] && grep -q "GITHUB_TOKEN" "$SAGE_REPO/.env"; then
            echo_info "Found GITHUB_TOKEN in .env, attempting to authenticate..."
            TOKEN=$(grep GITHUB_TOKEN "$SAGE_REPO/.env" | cut -d'=' -f2)
            if [ -n "$TOKEN" ]; then
                # Clear environment variable if set
                unset GITHUB_TOKEN
                echo "$TOKEN" | gh auth login --with-token --hostname github.com 2>/dev/null
                if gh auth status &> /dev/null; then
                    echo_success "Authenticated using token from .env"
                else
                    echo_error "Failed to authenticate with token from .env"
                    echo "Run: gh auth login"
                    exit 1
                fi
            fi
        else
            echo_error "Run: gh auth login"
            echo "Or add GITHUB_TOKEN to $SAGE_REPO/.env"
            exit 1
        fi
    fi

    echo_success "Prerequisites satisfied"
}

# Get SAGE repo path
get_sage_path() {
    # sage-edge 已独立到: https://github.com/intellistream/sage-edge
    # 此脚本仅用于历史记录，不再需要执行
    echo_error "sage-edge 已独立，请访问: https://github.com/intellistream/sage-edge"
    echo_error "安装: pip install isage-edge"
    exit 0
}

# Create GitHub repository
create_github_repo() {
    echo_info "Creating GitHub repository: intellistream/sage-edge"

    if gh repo view intellistream/sage-edge &> /dev/null; then
        echo_warning "Repository already exists. Skipping creation."
        REPO_EXISTS=1
    else
        gh repo create intellistream/sage-edge \
            --public \
            --description "SAGE Edge - Lightweight FastAPI aggregator for SAGE Gateway" \
            --license MIT \
            --clone

        cd sage-edge
        REPO_EXISTS=0
        echo_success "Repository created and cloned"
    fi
}

# Setup repository structure
setup_repo_structure() {
    echo_info "Setting up repository structure..."

    if [ $REPO_EXISTS -eq 1 ]; then
        # Clone if not already in directory
        if [ ! -d "sage-edge" ]; then
            gh repo clone intellistream/sage-edge
        fi
        cd sage-edge
    fi

    # Create directory structure
    mkdir -p src/sage/edge tests .github/workflows docs

    # Create __init__.py files
    touch src/sage/__init__.py
    touch tests/__init__.py

    echo_success "Directory structure created"
}

# Copy core files
copy_core_files() {
    echo_info "Copying core files from SAGE monorepo..."

    # Copy Python source files
    # 代码已迁移到独立仓库，此处代码不再有效
    echo "请从 https://github.com/intellistream/sage-edge 获取源码"

    # Update pyproject.toml URLs
    sed -i.bak 's|https://github.com/intellistream/SAGE|https://github.com/intellistream/sage-edge|g' pyproject.toml
    rm pyproject.toml.bak

    echo_success "Core files copied"
}

# Copy template files
copy_template_files() {
    echo_info "Copying template files..."

    DOCS_PATH="$SAGE_REPO/docs-public/docs_src/dev-notes/cross-layer/architecture"

    # README
    cp "$DOCS_PATH/sage-edge-standalone-README.md" README.md

    # CHANGELOG
    cp "$DOCS_PATH/sage-edge-standalone-CHANGELOG.md" CHANGELOG.md

    # CI/CD workflow
    cp "$DOCS_PATH/sage-edge-standalone-ci.yml" .github/workflows/ci.yml

    echo_success "Template files copied"
}

# Create additional files
create_additional_files() {
    echo_info "Creating additional files..."

    # .gitignore
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# MyPy
.mypy_cache/
.dmypy.json
dmypy.json

# Ruff
.ruff_cache/

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db
EOF

    # LICENSE
    cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 IntelliStream Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

    # CONTRIBUTING.md
    cat > CONTRIBUTING.md << 'EOF'
# Contributing to SAGE Edge

We welcome contributions! Please follow these guidelines:

## Development Setup

```bash
git clone https://github.com/intellistream/sage-edge.git
cd sage-edge
pip install -e .[dev]
```

## Guidelines

- Follow PEP 8 style guide
- Use Ruff for linting: `ruff check src/`
- Run tests before submitting: `pytest tests/ -v`
- Update CHANGELOG.md for notable changes

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For detailed guidelines, see [SAGE Contributing Guide](https://github.com/intellistream/SAGE/blob/main/CONTRIBUTING.md).
EOF

    echo_success "Additional files created"
}

# Create tests
create_tests() {
    echo_info "Creating test files..."

    cat > tests/test_app.py << 'EOF'
"""Tests for sage.edge.app module."""

import pytest
from sage.edge.app import create_app


def test_create_app_no_llm():
    """Test creating app without LLM gateway."""
    app = create_app(mount_llm=False)
    assert app.title == "SAGE Edge"
    assert "/healthz" in [route.path for route in app.router.routes]


def test_create_app_with_llm_default_mount():
    """Test creating app with LLM gateway at default path."""
    # This test requires Gateway to be installed
    pytest.skip("Requires isage-llm-gateway")


def test_create_app_with_llm_custom_prefix():
    """Test creating app with LLM gateway at custom prefix."""
    # This test requires Gateway to be installed
    pytest.skip("Requires isage-llm-gateway")
EOF

    cat > tests/conftest.py << 'EOF'
"""Pytest configuration for sage-edge tests."""

import pytest


@pytest.fixture
def mock_gateway_app():
    """Mock Gateway app for testing."""
    from fastapi import FastAPI
    app = FastAPI(title="Mock Gateway")
    return app
EOF

    echo_success "Test files created"
}

# Git commit and push
git_commit_push() {
    echo_info "Committing and pushing to GitHub..."

    git add .
    git commit -m "feat: initial release of sage-edge as independent package

- Core functionality: FastAPI aggregator for SAGE Gateway
- Default mounting at / with path preservation
- Custom prefix support
- Health check endpoints
- CLI entrypoint (sage-edge)
- Comprehensive documentation
- CI/CD with GitHub Actions

Related to SAGE monorepo: https://github.com/intellistream/SAGE"

    git push origin main

    # Create and push develop branch
    git checkout -b develop
    git push -u origin develop

    # Set develop as default branch
    gh repo edit intellistream/sage-edge --default-branch develop

    echo_success "Pushed to GitHub"
}

# Configure repository settings
configure_repo_settings() {
    echo_info "Configuring repository settings..."

    # Enable issues
    gh repo edit intellistream/sage-edge --enable-issues=true

    # Add topics
    gh repo edit intellistream/sage-edge \
        --add-topic sage \
        --add-topic llm \
        --add-topic fastapi \
        --add-topic openai \
        --add-topic gateway

    echo_success "Repository settings configured"
}

# Setup GitHub Secrets
setup_secrets() {
    echo_info "Setting up GitHub Secrets..."

    echo_warning "You need to manually set up PyPI tokens:"
    echo "1. Get PyPI token from: https://pypi.org/manage/account/token/"
    echo "2. Run: gh secret set PYPI_API_TOKEN -R intellistream/sage-edge"
    echo ""
    echo "3. Get TestPyPI token from: https://test.pypi.org/manage/account/token/"
    echo "4. Run: gh secret set TEST_PYPI_API_TOKEN -R intellistream/sage-edge"
    echo ""

    read -p "Press Enter when you have the tokens ready, or Ctrl+C to skip..."

    echo "Setting PYPI_API_TOKEN:"
    gh secret set PYPI_API_TOKEN -R intellistream/sage-edge

    echo "Setting TEST_PYPI_API_TOKEN:"
    gh secret set TEST_PYPI_API_TOKEN -R intellistream/sage-edge

    echo_success "GitHub Secrets configured"
}

# Print summary
print_summary() {
    echo ""
    echo_success "========================================="
    echo_success "SAGE Edge repository created successfully!"
    echo_success "========================================="
    echo ""
    echo_info "Repository: https://github.com/intellistream/sage-edge"
    echo_info "Local path: $(pwd)"
    echo ""
    echo_info "Next steps:"
    echo "1. Review the generated files"
    echo "2. Run local tests: pytest tests/ -v"
    echo "3. Test installation: pip install -e .[dev]"
    echo "4. Create release: git tag v0.1.0-beta1 && git push origin v0.1.0-beta1"
    echo "5. Monitor CI/CD: https://github.com/intellistream/sage-edge/actions"
    echo ""
}

# Main execution
main() {
    echo_info "================================================"
    echo_info "SAGE Edge Independent Repository Setup Script"
    echo_info "================================================"
    echo ""

    check_prerequisites
    get_sage_path
    create_github_repo
    setup_repo_structure
    copy_core_files
    copy_template_files
    create_additional_files
    create_tests
    git_commit_push
    configure_repo_settings
    setup_secrets
    print_summary
}

# Run main
main
