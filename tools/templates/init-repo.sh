#!/usr/bin/env bash
# init-repo.sh — initialise a SAGE repo from the template in tools/templates/new-repo/
#
# Usage:
#   cd /path/to/target-repo
#   /path/to/SAGE/tools/templates/init-repo.sh [OPTIONS]
#
# Options:
#   --pkg-name  NAME     PyPI package name          (e.g. isage-rag)
#   --pkg-mod   MODULE   Python import name          (e.g. sage_rag)
#   --desc      TEXT     Short description
#   --cpp                Also apply C++ extension skeleton (new-repo-cpp/)
#   --dry-run            Show what would be copied, but don't write
#   --force              Overwrite existing files
#
# Examples:
#   init-repo.sh --pkg-name isage-rag --pkg-mod sage_rag --desc "SAGE RAG components"
#   init-repo.sh --pkg-name isage-kernel --pkg-mod sage_kernel --cpp

set -euo pipefail

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Defaults ─────────────────────────────────────────────────────────────────
PKG_NAME=""
PKG_MOD=""
DESCRIPTION="SAGE package."
WITH_CPP=false
DRY_RUN=false
FORCE=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_PY="${SCRIPT_DIR}/new-repo"
TEMPLATE_CPP="${SCRIPT_DIR}/new-repo-cpp"
TARGET="$(pwd)"

# ─── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pkg-name)  PKG_NAME="$2";    shift 2 ;;
        --pkg-mod)   PKG_MOD="$2";     shift 2 ;;
        --desc)      DESCRIPTION="$2"; shift 2 ;;
        --cpp)       WITH_CPP=true;    shift ;;
        --dry-run)   DRY_RUN=true;     shift ;;
        --force)     FORCE=true;       shift ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
    esac
done

# ─── Validate ─────────────────────────────────────────────────────────────────
if [ -z "$PKG_NAME" ] || [ -z "$PKG_MOD" ]; then
    echo -e "${RED}Error: --pkg-name and --pkg-mod are required.${NC}"
    echo ""
    echo "Usage: $0 --pkg-name isage-rag --pkg-mod sage_rag --desc \"SAGE RAG\""
    exit 1
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  SAGE Repo Initialiser${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Target     : ${TARGET}"
echo -e "  PyPI name  : ${PKG_NAME}"
echo -e "  Import name: ${PKG_MOD}"
echo -e "  C++ ext    : ${WITH_CPP}"
echo -e "  Dry-run    : ${DRY_RUN}"
echo ""

# ─── Helpers ──────────────────────────────────────────────────────────────────
copy_file() {
    local src="$1"
    local dst="$2"

    if [ -f "$dst" ] && [ "$FORCE" = false ]; then
        echo -e "  ${YELLOW}skip${NC}  $dst  (already exists; use --force to overwrite)"
        return
    fi

    if [ "$DRY_RUN" = true ]; then
        echo -e "  ${CYAN}[dry]${NC}  $src → $dst"
        return
    fi

    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo -e "  ${GREEN}copy${NC}  $dst"
}

substitute() {
    # Replace template placeholders with real names in a file
    local file="$1"
    [ "$DRY_RUN" = true ] && return
    sed -i \
        -e "s/MY_PKG_NAME/${PKG_NAME}/g" \
        -e "s/my_pkg/${PKG_MOD}/g" \
        -e "s/Short description of the package\./${DESCRIPTION}/g" \
        -e "s/Short description\\./${DESCRIPTION}/g" \
        "$file"
}

# ─── Copy Python template files ───────────────────────────────────────────────
echo -e "${BOLD}Copying Python template files...${NC}"

# Non-hidden top-level files
for f in quickstart.sh pytest.ini ruff.toml codecov.yml; do
    copy_file "${TEMPLATE_PY}/${f}" "${TARGET}/${f}"
    [ -f "${TARGET}/${f}" ] && substitute "${TARGET}/${f}"
done

# pyproject.toml
copy_file "${TEMPLATE_PY}/pyproject.toml" "${TARGET}/pyproject.toml"
[ -f "${TARGET}/pyproject.toml" ] && substitute "${TARGET}/pyproject.toml"

# .pre-commit-config.yaml
copy_file "${TEMPLATE_PY}/.pre-commit-config.yaml" "${TARGET}/.pre-commit-config.yaml"
[ -f "${TARGET}/.pre-commit-config.yaml" ] && substitute "${TARGET}/.pre-commit-config.yaml"

# hooks/
for hook in pre-commit pre-push post-commit; do
    copy_file "${TEMPLATE_PY}/hooks/${hook}" "${TARGET}/hooks/${hook}"
    [ -f "${TARGET}/hooks/${hook}" ] && chmod +x "${TARGET}/hooks/${hook}"
done

# GitHub Actions workflows
for wf in ci.yml release.yml version-source-guard.yml back-sync.yml update-deps.yml; do
    copy_file "${TEMPLATE_PY}/.github/workflows/${wf}" "${TARGET}/.github/workflows/${wf}"
done

# Source package skeleton
PKG_SRC="${TARGET}/src/${PKG_MOD}"
if [ ! -d "$PKG_SRC" ] || [ "$FORCE" = true ]; then
    copy_file "${TEMPLATE_PY}/src/my_pkg/_version.py" "${PKG_SRC}/_version.py"
    copy_file "${TEMPLATE_PY}/src/my_pkg/__init__.py"  "${PKG_SRC}/__init__.py"
    [ "$DRY_RUN" = false ] && substitute "${PKG_SRC}/_version.py"
    [ "$DRY_RUN" = false ] && substitute "${PKG_SRC}/__init__.py"
fi

# Make quickstart.sh executable
[ "$DRY_RUN" = false ] && chmod +x "${TARGET}/quickstart.sh" 2>/dev/null || true

# ─── Copy C++ skeleton (optional) ─────────────────────────────────────────────
if [ "$WITH_CPP" = true ]; then
    echo ""
    echo -e "${BOLD}Copying C++ extension skeleton...${NC}"

    copy_file "${TEMPLATE_CPP}/CMakeLists.txt"       "${TARGET}/CMakeLists.txt"
    copy_file "${TEMPLATE_CPP}/pyproject.toml"        "${TARGET}/pyproject.toml"
    copy_file "${TEMPLATE_CPP}/build_manylinux.sh"    "${TARGET}/build_manylinux.sh"
    copy_file "${TEMPLATE_CPP}/csrc/bindings.cpp"     "${TARGET}/csrc/bindings.cpp"
    copy_file "${TEMPLATE_CPP}/.github/workflows/release.yml" \
              "${TARGET}/.github/workflows/release.yml"

    for f in CMakeLists.txt pyproject.toml csrc/bindings.cpp; do
        [ -f "${TARGET}/${f}" ] && substitute "${TARGET}/${f}"
    done

    # csrc/include placeholder
    if [ "$DRY_RUN" = false ]; then
        mkdir -p "${TARGET}/include/${PKG_MOD}"
        touch "${TARGET}/include/${PKG_MOD}/.gitkeep"
    fi

    [ "$DRY_RUN" = false ] && chmod +x "${TARGET}/build_manylinux.sh" || true
fi

echo ""
echo -e "${GREEN}${BOLD}✓ Done!${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. cd ${TARGET}"
echo -e "  2. Review and customise the generated files"
echo -e "  3. ./quickstart.sh   (installs post-commit / pre-push hooks)"
echo -e ""
echo -e "Release pipeline (cross-repo version linking):"
echo -e "  4. Set the DISPATCH_PAT secret in GitHub repo settings"
echo -e "     (PAT with 'repo' scope to dispatch to downstream repos)"
echo -e "  5. Edit .github/workflows/release.yml — set DOWNSTREAM_REPOS"
echo -e "     to the list of repos that depend on this package"
echo -e "  6. Downstream repos receive update-deps.yml automatically —"
echo -e "     they will auto-PR when an upstream package is released"
echo ""
