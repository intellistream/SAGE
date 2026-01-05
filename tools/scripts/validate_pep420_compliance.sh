#!/bin/bash
# validate_pep420_compliance.sh
# Validates PEP 420 namespace package compliance for SAGE monorepo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🔍 Validating PEP 420 namespace package compliance (SAGE monorepo)..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Check 1: No src/sage/__init__.py in any package
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Check 1: Namespace package __init__.py compliance"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Find all src/sage/__init__.py files (should be none)
VIOLATIONS=$(find "$PROJECT_ROOT/packages" -type f -path "*/src/sage/__init__.py" 2>/dev/null || true)

if [ -n "$VIOLATIONS" ]; then
    echo -e "${RED}❌ FAIL: Found prohibited src/sage/__init__.py files:${NC}"
    echo "$VIOLATIONS" | sed 's/^/   /'
    echo ""
    echo "   PEP 420 requires namespace packages to be implicit (no __init__.py)"
    echo "   Solution: rm packages/*/src/sage/__init__.py"
    echo "   See: docs-public/docs_src/dev-notes/cross-layer/pep420-namespace-migration.md"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ PASS: No src/sage/__init__.py files found${NC}"
fi
echo ""

# Check 2: All packages have "namespaces = true"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Check 2: pyproject.toml namespace configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MISSING_NAMESPACES=()
for TOML in "$PROJECT_ROOT"/packages/*/pyproject.toml; do
    if [ -f "$TOML" ]; then
        PACKAGE=$(basename "$(dirname "$TOML")")
        if ! grep -q "namespaces = true" "$TOML"; then
            MISSING_NAMESPACES+=("$PACKAGE")
        fi
    fi
done

if [ ${#MISSING_NAMESPACES[@]} -gt 0 ]; then
    echo -e "${RED}❌ FAIL: Missing 'namespaces = true' in packages:${NC}"
    printf '   - %s\n' "${MISSING_NAMESPACES[@]}"
    echo ""
    echo "   Add to [tool.setuptools.packages.find] section:"
    echo "   namespaces = true"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ PASS: All packages have 'namespaces = true'${NC}"
fi
echo ""

# Check 3: Runtime behavior (if packages are installed)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Check 3: Runtime namespace package behavior"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test if sage namespace is implicit
RUNTIME_TEST=$(python3 -c "
import sys
try:
    import sage
    file = getattr(sage, '__file__', None)
    if file is None:
        print('PASS')
    else:
        print(f'FAIL:{file}')
except ImportError:
    print('PASS')  # Also valid for PEP 420
" 2>&1 || echo "ERROR")

if [[ "$RUNTIME_TEST" == "PASS" ]]; then
    echo -e "${GREEN}✓ PASS: sage namespace is implicit (PEP 420 compliant)${NC}"
elif [[ "$RUNTIME_TEST" =~ ^FAIL: ]]; then
    HIJACKER="${RUNTIME_TEST#FAIL:}"
    echo -e "${RED}❌ FAIL: sage namespace has __file__: $HIJACKER${NC}"
    echo "   This indicates namespace hijacking by external package"
    echo "   Solution: Update external package to PEP 420 or uninstall"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${YELLOW}⚠️  WARNING: Could not test runtime behavior${NC}"
    echo "   Packages may not be installed yet"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}   ($WARNINGS warnings)${NC}"
    fi
    exit 0
else
    echo -e "${RED}❌ $ERRORS check(s) failed${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}   ($WARNINGS warnings)${NC}"
    fi
    echo ""
    echo "See: docs-public/docs_src/dev-notes/cross-layer/pep420-namespace-migration.md"
    exit 1
fi
