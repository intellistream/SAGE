#!/bin/bash
# Setup script for sageLLM development environment
# Run this after cloning the repository

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}sageLLM Development Setup${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}1. Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo -e "${GREEN}✅ Python $python_version (>= 3.10)${NC}"
else
    echo -e "${RED}❌ Python $python_version is too old. Requires Python >= 3.10${NC}"
    exit 1
fi
echo ""

# Install package with dev dependencies
echo -e "${YELLOW}2. Installing sageLLM with development dependencies...${NC}"
if pip install -e ".[dev]" --quiet; then
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi
echo ""

# Install pre-commit hooks
echo -e "${YELLOW}3. Installing pre-commit hooks...${NC}"
if pre-commit install; then
    echo -e "${GREEN}✅ Pre-commit hooks installed${NC}"
else
    echo -e "${RED}❌ Failed to install pre-commit hooks${NC}"
    exit 1
fi
echo ""

# Optional: Run pre-commit on all files
read -p "$(echo -e ${YELLOW}Do you want to run pre-commit checks on all files now? [y/N]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Running pre-commit on all files...${NC}"
    if pre-commit run --all-files; then
        echo -e "${GREEN}✅ All checks passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some checks failed (files may have been auto-fixed)${NC}"
        echo -e "${YELLOW}Please review the changes and commit them${NC}"
    fi
else
    echo -e "${BLUE}Skipped. You can run it later with: pre-commit run --all-files${NC}"
fi
echo ""

# Setup complete
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Next steps:"
echo "  • Read DEVELOPMENT.md for development guidelines"
echo "  • Run tests: pytest"
echo "  • Check code quality: pre-commit run --all-files"
echo ""
echo "Pre-commit will now run automatically before each commit."
echo "To skip temporarily: git commit --no-verify"
echo ""
