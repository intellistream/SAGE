#!/bin/bash
# SageVDB Quickstart Script
# Sets up development environment and git hooks

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Print banner
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}   ____                  __     ______  ____ ${NC}"
echo -e "${BOLD}${BLUE}  / __/__  ___  ___     / /    / __  / / __ )${NC}"
echo -e "${BOLD}${BLUE} _\\ \/ _ \/ _ \/ -_)   / /    / / / / / __  |${NC}"
echo -e "${BOLD}${BLUE}/___/\\___/\\_, /\\__/   /_/    /_/ /_/ /____/ ${NC}"
echo -e "${BOLD}${BLUE}         /___/                               ${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}SageVDB Quickstart Setup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${BLUE}📂 Project root: ${NC}$PROJECT_ROOT"
echo ""

# Step 1: Install git hooks
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}Step 1: Installing Git Hooks${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
TEMPLATE_DIR="$PROJECT_ROOT/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo -e "${RED}✗ Git repository not initialized${NC}"
    echo -e "${YELLOW}Run: git init${NC}"
    exit 1
fi

# Install pre-commit hook
if [ -f "$TEMPLATE_DIR/pre-commit" ]; then
    cp "$TEMPLATE_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
    echo -e "${GREEN}✓ Installed pre-commit hook${NC}"
else
    echo -e "${YELLOW}⚠  pre-commit template not found, skipping${NC}"
fi

# Install pre-push hook
if [ -f "$TEMPLATE_DIR/pre-push" ]; then
    cp "$TEMPLATE_DIR/pre-push" "$HOOKS_DIR/pre-push"
    chmod +x "$HOOKS_DIR/pre-push"
    echo -e "${GREEN}✓ Installed pre-push hook${NC}"
else
    echo -e "${YELLOW}⚠  pre-push template not found, skipping${NC}"
fi

echo ""

# Step 2: Check dependencies
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}Step 2: Checking Dependencies${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check for CMake
if command -v cmake &> /dev/null; then
    CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
    echo -e "${GREEN}✓ CMake found: ${NC}v$CMAKE_VERSION"
else
    echo -e "${RED}✗ CMake not found${NC}"
    echo -e "${YELLOW}  Install: sudo apt install cmake  # or  brew install cmake${NC}"
fi

# Check for C++ compiler
if command -v g++ &> /dev/null; then
    GCC_VERSION=$(g++ --version | head -n1 | awk '{print $NF}')
    echo -e "${GREEN}✓ g++ found: ${NC}v$GCC_VERSION"
elif command -v clang++ &> /dev/null; then
    CLANG_VERSION=$(clang++ --version | head -n1 | awk '{print $NF}')
    echo -e "${GREEN}✓ clang++ found: ${NC}v$CLANG_VERSION"
else
    echo -e "${RED}✗ C++ compiler not found${NC}"
    echo -e "${YELLOW}  Install: sudo apt install build-essential  # or  xcode-select --install${NC}"
fi

# Check for Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓ Python found: ${NC}v$PYTHON_VERSION"
else
    echo -e "${RED}✗ Python not found${NC}"
fi

# Check for sage-pypi-publisher
if command -v sage-pypi-publisher &> /dev/null; then
    echo -e "${GREEN}✓ sage-pypi-publisher found${NC}"
else
    echo -e "${YELLOW}⚠  sage-pypi-publisher not found${NC}"
    echo -e "${YELLOW}  Optional for PyPI publishing: pip install sage-pypi-publisher${NC}"
fi

echo ""

# Step 3: Build instructions
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}Step 3: Build Options${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${BLUE}Would you like to build the project now?${NC}"
echo -e "  ${GREEN}[y]${NC} Yes, configure and build"
echo -e "  ${YELLOW}[n]${NC} No, I'll build manually later"
echo -n "Your choice [y/n]: "
read -r BUILD_NOW

if [[ "$BUILD_NOW" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🔨 Building SageVDB...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -f "$PROJECT_ROOT/build.sh" ]; then
        echo -e "${YELLOW}Using build.sh script...${NC}"
        cd "$PROJECT_ROOT"
        bash build.sh
    else
        echo -e "${YELLOW}Configuring with CMake...${NC}"
        cmake -B "$PROJECT_ROOT/build" -S "$PROJECT_ROOT" \
            -DCMAKE_BUILD_TYPE=Release \
            -DBUILD_TESTS=ON

        echo -e "${YELLOW}Building...${NC}"
        cmake --build "$PROJECT_ROOT/build" -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

        echo -e "${GREEN}✓ Build complete${NC}"
    fi
else
    echo -e "${YELLOW}Skipping build. To build later, run:${NC}"
    echo -e "  ${CYAN}./build.sh${NC}"
    echo -e "${YELLOW}Or manually:${NC}"
    echo -e "  ${CYAN}cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON${NC}"
    echo -e "  ${CYAN}cmake --build build -j\$(nproc)${NC}"
fi

echo ""

# Step 4: Python package setup
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}${BOLD}Step 4: Python Package Setup (Optional)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${BLUE}Install Python package in development mode?${NC}"
echo -e "  ${GREEN}[y]${NC} Yes, install with pip install -e ."
echo -e "  ${YELLOW}[n]${NC} No, skip Python setup"
echo -n "Your choice [y/n]: "
read -r INSTALL_PY

if [[ "$INSTALL_PY" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Installing in editable mode...${NC}"
    cd "$PROJECT_ROOT"
    pip install -e .
    echo -e "${GREEN}✓ Python package installed${NC}"
else
    echo -e "${YELLOW}Skipping Python package install${NC}"
fi

echo ""

# Summary
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}✓ Setup Complete!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}${BOLD}Next Steps:${NC}"
echo -e "  ${CYAN}1.${NC} Run tests: ${CYAN}cd build && ctest --verbose${NC}"
echo -e "  ${CYAN}2.${NC} Try examples: ${CYAN}python examples/python_persistence_example.py${NC}"
echo -e "  ${CYAN}3.${NC} Read docs: ${CYAN}cat README.md${NC}"
echo ""
echo -e "${YELLOW}${BOLD}Git Hooks Installed:${NC}"
echo -e "  ${GREEN}•${NC} pre-commit: Checks code quality before commits"
echo -e "  ${GREEN}•${NC} pre-push: Manages version updates and PyPI publishing"
echo ""
echo -e "${BLUE}${BOLD}Useful Commands:${NC}"
echo -e "  ${CYAN}./build.sh${NC}                    - Quick rebuild"
echo -e "  ${CYAN}sage-pypi-publisher build${NC}     - Build distribution packages"
echo -e "  ${CYAN}sage-pypi-publisher publish${NC}   - Build and publish to PyPI"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
