#!/usr/bin/env bash
# =============================================================================
# SAGE Tool Version Checker
# =============================================================================
# Checks if locally installed tool versions match pre-commit-config.yaml
# This prevents CI/local environment discrepancies.
#
# Usage:
#   ./tools/install/check_tool_versions.sh [--fix]
#
# Options:
#   --fix    Automatically update tools to match pre-commit-config.yaml versions
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRE_COMMIT_CONFIG="$REPO_ROOT/tools/pre-commit-config.yaml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FIX_MODE=false
QUIET_MODE=false
for arg in "$@"; do
    case $arg in
        --fix)
            FIX_MODE=true
            ;;
        --quiet|-q)
            QUIET_MODE=true
            ;;
    esac
done

log_info() {
    if [[ "$QUIET_MODE" != "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ "$QUIET_MODE" != "true" ]]; then
        echo -e "${GREEN}[OK]${NC} $1"
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Extract version from pre-commit-config.yaml for a given repo
get_precommit_version() {
    local repo_pattern="$1"
    grep -A1 "$repo_pattern" "$PRE_COMMIT_CONFIG" | grep "rev:" | head -1 | sed 's/.*rev: *v\?//' | tr -d '[:space:]'
}

# Get locally installed version
get_local_version() {
    local tool="$1"
    case $tool in
        ruff)
            ruff --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo ""
            ;;
        pre-commit)
            pre-commit --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo ""
            ;;
        mypy)
            mypy --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo ""
            ;;
        *)
            echo ""
            ;;
    esac
}

# Compare versions (returns 0 if equal, 1 if different)
compare_versions() {
    local v1="$1"
    local v2="$2"
    [[ "$v1" == "$v2" ]]
}

# Main check function
check_tool_versions() {
    local has_mismatch=false

    log_info "Checking tool versions against pre-commit-config.yaml..."
    echo ""

    # Check ruff
    local ruff_precommit_version
    ruff_precommit_version=$(get_precommit_version "astral-sh/ruff-pre-commit")
    local ruff_local_version
    ruff_local_version=$(get_local_version "ruff")

    if [[ -z "$ruff_local_version" ]]; then
        log_warn "ruff: not installed locally"
        has_mismatch=true
    elif compare_versions "$ruff_local_version" "$ruff_precommit_version"; then
        log_success "ruff: $ruff_local_version (matches pre-commit config)"
    else
        log_warn "ruff: local=$ruff_local_version, pre-commit=$ruff_precommit_version (MISMATCH)"
        has_mismatch=true
    fi

    # Check pyproject.toml consistency
    echo ""
    log_info "Checking pyproject.toml ruff versions..."
    local pyproject_mismatch=false
    for pyproject in "$REPO_ROOT"/packages/*/pyproject.toml; do
        if [[ -f "$pyproject" ]]; then
            local pkg_name
            pkg_name=$(basename "$(dirname "$pyproject")")
            local pkg_ruff_version
            pkg_ruff_version=$(grep -oP '"ruff==\K[0-9.]+' "$pyproject" 2>/dev/null || echo "")

            if [[ -z "$pkg_ruff_version" ]]; then
                # Check if it uses >= instead of ==
                local loose_version
                loose_version=$(grep -oP '"ruff>=\K[0-9.]+' "$pyproject" 2>/dev/null || echo "")
                if [[ -n "$loose_version" ]]; then
                    log_warn "$pkg_name: ruff>=$loose_version (should be ruff==$ruff_precommit_version)"
                    pyproject_mismatch=true
                fi
                # No ruff dependency in this package is OK
            elif [[ "$pkg_ruff_version" != "$ruff_precommit_version" ]]; then
                log_warn "$pkg_name: ruff==$pkg_ruff_version (should be $ruff_precommit_version)"
                pyproject_mismatch=true
            else
                log_success "$pkg_name: ruff==$pkg_ruff_version"
            fi
        fi
    done

    if [[ "$pyproject_mismatch" == "true" ]]; then
        has_mismatch=true
    fi

    # Check pre-commit-hooks version
    echo ""
    local hooks_precommit_version
    hooks_precommit_version=$(get_precommit_version "pre-commit/pre-commit-hooks")
    log_info "pre-commit-hooks: using v$hooks_precommit_version in config"

    echo ""

    if [[ "$has_mismatch" == "true" ]]; then
        if [[ "$FIX_MODE" == "true" ]]; then
            log_info "Attempting to fix version mismatches..."
            fix_versions "$ruff_precommit_version"
        else
            echo ""
            echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${YELLOW}⚠️  Tool version mismatch detected.${NC}"
            echo ""
            echo "This may cause different behavior between local and CI environments."
            echo ""
            echo "To fix automatically, run:"
            echo -e "  ${GREEN}./tools/install/check_tool_versions.sh --fix${NC}"
            echo ""
            echo "Or manually install the correct versions:"
            if [[ -n "$ruff_precommit_version" ]] && [[ "$ruff_local_version" != "$ruff_precommit_version" ]]; then
                echo -e "  ${BLUE}pip install ruff==$ruff_precommit_version${NC}"
            fi
            echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            return 1
        fi
    else
        log_success "All tool versions match pre-commit config."
    fi

    return 0
}

fix_versions() {
    local ruff_version="$1"

    if [[ -n "$ruff_version" ]]; then
        log_info "Installing ruff==$ruff_version..."
        pip install "ruff==$ruff_version" --quiet
        log_success "ruff updated to $ruff_version"
    fi

    # Update pre-commit hooks cache
    log_info "Updating pre-commit hook cache..."
    pre-commit clean --config "$PRE_COMMIT_CONFIG" 2>/dev/null || true
    pre-commit install-hooks --config "$PRE_COMMIT_CONFIG" 2>/dev/null || true

    log_success "Tool versions synchronized."
}

# Run the check
check_tool_versions
