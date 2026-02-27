#!/usr/bin/env bash
# quickstart.sh — SAGE repo dev environment setup
#
# Usage:
#   ./quickstart.sh             # full setup (default)
#   ./quickstart.sh --dev       # alias for full setup
#   ./quickstart.sh --yes       # non-interactive (assume yes)
#   ./quickstart.sh --doctor    # diagnose environment issues
#
# Rules:
#   - NEVER creates a new venv.  Must be called inside an existing conda/venv.
#   - Installs hooks via pre-commit + direct symlinks for post-commit / pre-push.
#   - Installs the package in editable mode: pip install -e .[dev]

set -e

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Arguments ────────────────────────────────────────────────────────────────
MODE="dev"
YES=false
for arg in "$@"; do
    case "$arg" in
        --doctor)   MODE="doctor" ;;
        --dev)      MODE="dev" ;;
        --yes|-y)   YES=true ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}  $(basename "$PROJECT_ROOT") — Quick Start${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ─── Doctor ───────────────────────────────────────────────────────────────────
if [ "$MODE" = "doctor" ]; then
    echo -e "${BOLD}${BLUE}Environment Diagnosis${NC}"
    echo ""
    echo -e "${YELLOW}Python:${NC} $(python3 --version 2>/dev/null || echo 'NOT FOUND')"
    echo -e "${YELLOW}Conda env:${NC} ${CONDA_DEFAULT_ENV:-none}"
    echo -e "${YELLOW}Venv:${NC} ${VIRTUAL_ENV:-none}"
    echo -e "${YELLOW}pre-commit:${NC} $(pre-commit --version 2>/dev/null || echo 'NOT FOUND')"
    echo -e "${YELLOW}ruff:${NC} $(ruff --version 2>/dev/null || echo 'NOT FOUND')"
    echo -e "${YELLOW}pytest:${NC} $(pytest --version 2>/dev/null || echo 'NOT FOUND')"
    echo ""
    echo -e "${YELLOW}Git hooks installed:${NC}"
    for h in pre-commit pre-push post-commit; do
        if [ -f "$PROJECT_ROOT/.git/hooks/$h" ]; then
            echo -e "  ${GREEN}✓ $h${NC}"
        else
            echo -e "  ${RED}✗ $h${NC}"
        fi
    done
    exit 0
fi

# ─── Step 0: Require an active environment ────────────────────────────────────
if [ -z "$CONDA_DEFAULT_ENV" ] && [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}  ❌ No Python environment detected.${NC}"
    echo -e "${YELLOW}  → Activate a conda or venv environment first:${NC}"
    echo -e "     conda create -n sage python=3.11 && conda activate sage"
    echo ""
    echo -e "${RED}  ⚠️  NEVER run this script without an active environment.${NC}"
    echo -e "${RED}  ⚠️  This script will NOT create a new environment for you.${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ Environment: ${CONDA_DEFAULT_ENV:-$VIRTUAL_ENV}${NC}"
echo ""

# ─── Step 1: Python version check ────────────────────────────────────────────
echo -e "${YELLOW}${BOLD}Step 1/4: Python version${NC}"
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" || {
    echo -e "${RED}✗ Python $PYTHON_VERSION is too old (requires >= 3.10)${NC}"
    exit 1
}
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
echo ""

# ─── Step 2: Install Git Hooks ───────────────────────────────────────────────
echo -e "${YELLOW}${BOLD}Step 2/4: Installing Git Hooks${NC}"

HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
TEMPLATE_HOOKS="$PROJECT_ROOT/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo -e "${YELLOW}⚠  .git directory not found — skipping hooks (not a git repo?)${NC}"
else
    # pre-commit hook managed by the pre-commit framework
    if command -v pre-commit >/dev/null 2>&1; then
        pre-commit install --install-hooks 2>/dev/null
        echo -e "${GREEN}✓ pre-commit hook installed${NC}"
    else
        echo -e "${YELLOW}⚠  pre-commit not found; installing...${NC}"
        pip install pre-commit --quiet
        pre-commit install --install-hooks 2>/dev/null
        echo -e "${GREEN}✓ pre-commit installed and hook set up${NC}"
    fi

    # pre-push and post-commit — symlinked from hooks/
    for hook in pre-push post-commit; do
        if [ -f "$TEMPLATE_HOOKS/$hook" ]; then
            ln -sf "../../hooks/$hook" "$HOOKS_DIR/$hook"
            chmod +x "$HOOKS_DIR/$hook"
            echo -e "${GREEN}✓ $hook hook linked${NC}"
        else
            echo -e "${YELLOW}⚠  hooks/$hook not found, skipping${NC}"
        fi
    done
fi
echo ""

# ─── Step 3: Install package ─────────────────────────────────────────────────
echo -e "${YELLOW}${BOLD}Step 3/4: Installing package (editable)${NC}"
if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
    pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e . --quiet
    echo -e "${GREEN}✓ Package installed in editable mode${NC}"
else
    echo -e "${YELLOW}⚠  No pyproject.toml found — skipping package install${NC}"
fi
echo ""

# ─── Step 4: Sanity check ────────────────────────────────────────────────────
echo -e "${YELLOW}${BOLD}Step 4/4: Sanity check${NC}"
if command -v ruff >/dev/null 2>&1; then
    echo -e "${GREEN}✓ ruff $(ruff --version | awk '{print $2}')${NC}"
else
    echo -e "${YELLOW}⚠  ruff not found — install: pip install ruff${NC}"
fi
if command -v pytest >/dev/null 2>&1; then
    echo -e "${GREEN}✓ pytest available${NC}"
fi
echo ""

echo -e "${GREEN}${BOLD}✓ Setup complete!${NC}"
echo ""
echo -e "${BLUE}${BOLD}Next steps:${NC}"
echo -e "  ${CYAN}pytest -v${NC}              — run tests"
echo -e "  ${CYAN}ruff check src/${NC}        — lint"
echo -e "  ${CYAN}ruff format src/${NC}       — format"
echo -e "  ${CYAN}./quickstart.sh --doctor${NC} — diagnose environment"
echo ""
