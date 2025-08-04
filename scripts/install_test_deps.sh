#!/bin/bash

# Install Test Dependencies Script
# This script ensures all necessary test dependencies are installed across all SAGE packages

set -e

echo "🔧 Installing SAGE Test Dependencies..."

# Color output functions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to install package dependencies
install_package_deps() {
    local package_path=$1
    local package_name=$2
    
    if [ -f "$package_path/pyproject.toml" ]; then
        log_info "Installing test dependencies for $package_name..."
        cd "$package_path"
        
        # Install development dependencies if they exist
        if grep -q "\[project.optional-dependencies\]" pyproject.toml; then
            if grep -q "dev\s*=" pyproject.toml; then
                pip install -e ".[dev]" || log_warning "Failed to install dev dependencies for $package_name"
            fi
            if grep -q "testing\s*=" pyproject.toml; then
                pip install -e ".[testing]" || log_warning "Failed to install testing dependencies for $package_name"
            fi
        fi
        
        # Install the package itself in editable mode
        pip install -e . || log_warning "Failed to install $package_name in editable mode"
        
        log_success "Completed $package_name"
        cd - > /dev/null
    else
        log_warning "No pyproject.toml found in $package_path"
    fi
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info "Project root: $PROJECT_ROOT"

# Install core pytest dependencies first
log_info "Installing core pytest dependencies..."
pip install \
    "pytest>=7.0.0" \
    "pytest-cov>=4.0.0" \
    "pytest-asyncio>=0.21.0" \
    "pytest-benchmark>=4.0.0" \
    "pytest-mock>=3.10.0" \
    "pytest-xdist>=3.0.0" \
    "pytest-timeout>=2.1.0"

log_success "Core pytest dependencies installed"

# Install dev-toolkit first (since sage-dev depends on it)
log_info "Installing dev-toolkit..."
install_package_deps "$PROJECT_ROOT/dev-toolkit" "dev-toolkit"

# Install SAGE packages
log_info "Installing SAGE package dependencies..."

# Install packages in dependency order
PACKAGES=(
    "packages/sage-kernel"
    "packages/sage-middleware" 
    "packages/sage-userspace"
)

for package_dir in "${PACKAGES[@]}"; do
    package_path="$PROJECT_ROOT/$package_dir"
    package_name=$(basename "$package_dir")
    
    if [ -d "$package_path" ]; then
        install_package_deps "$package_path" "$package_name"
    else
        log_warning "Package directory not found: $package_path"
    fi
done

# Install main project
log_info "Installing main SAGE project..."
cd "$PROJECT_ROOT"
if [ -f "pyproject.toml" ]; then
    pip install -e ".[dev]" || log_warning "Failed to install main project dev dependencies"
    log_success "Main project installed"
else
    log_warning "No pyproject.toml found in project root"
fi

# Verify pytest-benchmark installation
log_info "Verifying pytest-benchmark installation..."
if python -c "import pytest_benchmark" 2>/dev/null; then
    log_success "pytest-benchmark is available"
else
    log_error "pytest-benchmark is not available, trying to install..."
    pip install pytest-benchmark>=4.0.0
    if python -c "import pytest_benchmark" 2>/dev/null; then
        log_success "pytest-benchmark installed successfully"
    else
        log_error "Failed to install pytest-benchmark"
        exit 1
    fi
fi

# Test sage-dev functionality
log_info "Testing sage-dev installation..."
if command -v sage-dev &> /dev/null; then
    log_success "sage-dev command is available"
    sage-dev --version || log_warning "sage-dev version check failed"
else
    log_warning "sage-dev command not found in PATH"
    log_info "You may need to restart your shell or update your PATH"
fi

log_success "🎉 All test dependencies installed successfully!"
log_info "You can now run tests with: sage-dev test"
log_info "Or run tests manually with: pytest tests/"
