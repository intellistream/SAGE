#!/usr/bin/env bash
# Developer helper script for SAGE project
# Provides common commands for development workflow

# ⚠️ 此脚本正在逐步迁移到 sage-dev CLI
# 📝 新用法: sage-dev <command>
# 🚀 建议使用新的 CLI 命令以获得更好的体验

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Helper functions
print_header() {
    echo -e "${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Show usage
usage() {
    cat << EOF
sage-development Helper Script

Usage: $0 <command> [options]

Commands:
  setup             Initial setup for development (install pre-commit, deps)
  install           Install SAGE in development mode
  test              Run all tests
  test-unit         Run unit tests only
  test-integration  Run integration tests only
  lint              Run all linters (ruff, mypy, shellcheck)
  format            Format code (black, isort)
  check             Run format check without modifying files
  pre-commit        Run pre-commit hooks on all files
  clean             Clean build artifacts and caches
  docs              Build documentation locally
  serve-docs        Serve documentation locally
  validate          Run all checks (lint, format check, test)
  help              Show this help message

Examples:
  $0 setup          # First time setup
  $0 format         # Format all Python code
  $0 test           # Run all tests
  $0 validate       # Run full validation suite

Environment Variables:
  SAGE_ENV          Python environment (conda, venv, system)
  SAGE_VERBOSE      Set to 1 for verbose output

EOF
}

# Setup development environment
cmd_setup() {
    print_header "Setting up development environment"

    # Check if pre-commit is installed
    if ! command -v pre-commit &> /dev/null; then
        print_info "Installing pre-commit..."
        pip install pre-commit
    fi

    # Install pre-commit hooks
    print_info "Installing pre-commit hooks..."
    pre-commit install
    print_success "Pre-commit hooks installed"

    # Install development dependencies
    print_info "Installing development dependencies..."
    pip install -e ".[dev]" || {
        print_warning "Failed to install with [dev] extras, trying basic install..."
        pip install -e .
    }

    # Install additional dev tools
    print_info "Installing additional dev tools..."
    pip install black isort ruff mypy pytest pytest-cov pre-commit detect-secrets

    print_success "Development environment setup complete!"
    print_info "Run '$0 validate' to verify everything works"
}

# Install in development mode
cmd_install() {
    print_header "Installing SAGE in development mode"
    pip install -e .
    print_success "SAGE installed in development mode"
}

# Run tests
cmd_test() {
    print_header "Running all tests"
    pytest tests/ -v --cov=packages --cov-report=term-missing
}

cmd_test_unit() {
    print_header "Running unit tests"
    pytest tests/ -v -m "not integration" --cov=packages --cov-report=term-missing
}

cmd_test_integration() {
    print_header "Running integration tests"
    pytest tests/ -v -m integration --cov=packages --cov-report=term-missing
}

# Linting
cmd_lint() {
    print_header "Running linters"

    print_info "Running ruff..."
    ruff check packages/ examples/ scripts/ || print_warning "Ruff found issues"

    print_info "Running mypy..."
    mypy packages/ --ignore-missing-imports || print_warning "Mypy found issues"

    print_info "Running shellcheck..."
    find . -name "*.sh" -not -path "./tools/conda/*" -exec shellcheck {} + || print_warning "Shellcheck found issues"

    print_success "Linting complete"
}

# Format code
cmd_format() {
    print_header "Formatting code"

    print_info "Running black..."
    black packages/ examples/ scripts/ --line-length 100

    print_info "Running isort..."
    isort packages/ examples/ scripts/ --profile black --line-length 100

    print_success "Code formatted"
}

# Check formatting without modifying
cmd_check() {
    print_header "Checking code format"

    print_info "Checking with black..."
    black packages/ examples/ scripts/ --check --line-length 100

    print_info "Checking with isort..."
    isort packages/ examples/ scripts/ --check --profile black --line-length 100

    print_success "Format check complete"
}

# Run pre-commit hooks
cmd_pre_commit() {
    print_header "Running pre-commit hooks"
    pre-commit run --all-files
    print_success "Pre-commit checks complete"
}

# Clean build artifacts
cmd_clean() {
    echo "⚠️  此命令已迁移到 sage-dev CLI"
    echo "新用法: sage-dev project clean"
    echo ""
    echo "继续使用旧命令..."
    echo ""
    
    print_header "Cleaning build artifacts"

    print_info "Removing Python cache files..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

    print_info "Removing build directories..."
    rm -rf build/ dist/ .eggs/

    print_info "Removing test and coverage artifacts..."
    rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/

    print_info "Removing empty directories in packages..."
    # Find and remove empty directories in packages, excluding .git directories
    # Use a loop to handle deeply nested empty directories
    for i in {1..5}; do
        find packages/ -type d -empty -not -path "*/.git/*" -delete 2>/dev/null || true
    done

    print_success "Clean complete"
}

# Build documentation
cmd_docs() {
    echo "⚠️  此命令已迁移到 sage-dev CLI"
    echo "新用法: sage-dev docs build"
    echo ""
    echo "继续使用旧命令..."
    echo ""
    
    print_header "Building documentation"
    cd docs-public

    if [ -f "build.sh" ]; then
        ./build.sh
    elif command -v mkdocs &> /dev/null; then
        mkdocs build
    else
        print_error "mkdocs not found. Install with: pip install mkdocs mkdocs-material"
        exit 1
    fi

    print_success "Documentation built"
}

# Serve documentation
cmd_serve_docs() {
    echo "⚠️  此命令已迁移到 sage-dev CLI"
    echo "新用法: sage-dev docs serve"
    echo ""
    echo "继续使用旧命令..."
    echo ""
    
    print_header "Serving documentation"
    cd docs-public

    if command -v mkdocs &> /dev/null; then
        mkdocs serve
    else
        print_error "mkdocs not found. Install with: pip install mkdocs mkdocs-material"
        exit 1
    fi
}

# Run full validation
cmd_validate() {
    print_header "Running full validation suite"

    local failed=0

    print_info "Step 1/4: Checking code format..."
    if ! cmd_check; then
        print_error "Format check failed"
        ((failed++))
    fi

    print_info "Step 2/4: Running linters..."
    if ! cmd_lint; then
        print_error "Linting failed"
        ((failed++))
    fi

    print_info "Step 3/4: Running tests..."
    if ! cmd_test; then
        print_error "Tests failed"
        ((failed++))
    fi

    print_info "Step 4/4: Running pre-commit hooks..."
    if ! cmd_pre_commit; then
        print_error "Pre-commit hooks failed"
        ((failed++))
    fi

    if [ $failed -eq 0 ]; then
        print_success "All validation checks passed!"
        return 0
    else
        print_error "Validation failed with $failed error(s)"
        return 1
    fi
}

# Main command dispatcher
main() {
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi

    local command=$1
    shift

    case "$command" in
        setup)
            cmd_setup "$@"
            ;;
        install)
            cmd_install "$@"
            ;;
        test)
            cmd_test "$@"
            ;;
        test-unit)
            cmd_test_unit "$@"
            ;;
        test-integration)
            cmd_test_integration "$@"
            ;;
        lint)
            cmd_lint "$@"
            ;;
        format)
            cmd_format "$@"
            ;;
        check)
            cmd_check "$@"
            ;;
        pre-commit)
            cmd_pre_commit "$@"
            ;;
        clean)
            cmd_clean "$@"
            ;;
        docs)
            cmd_docs "$@"
            ;;
        serve-docs)
            cmd_serve_docs "$@"
            ;;
        validate)
            cmd_validate "$@"
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
