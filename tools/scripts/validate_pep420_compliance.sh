#!/bin/bash
# validate_pep420_compliance.sh
# Validates PEP 420 namespace package compliance for sage-benchmark

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔍 Validating PEP 420 namespace package compliance..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Check 1: src/sage/__init__.py should not have pkgutil/pkg_resources
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Check 1: Namespace package __init__.py compliance"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

INIT_FILE="$PROJECT_ROOT/src/sage/__init__.py"

if [ ! -f "$INIT_FILE" ]; then
    echo -e "${YELLOW}⚠️  WARNING: $INIT_FILE not found${NC}"
    echo "   PEP 420 allows namespace packages without __init__.py"
    echo "   but having an empty one is also acceptable"
    WARNINGS=$((WARNINGS + 1))
else
    # Check for old-style namespace declarations
    if grep -qE "pkgutil|pkg_resources|__path__.*extend_path|declare_namespace" "$INIT_FILE"; then
        echo -e "${RED}❌ FAIL: Old-style namespace declarations found in $INIT_FILE${NC}"
        echo ""
        echo "   Problematic patterns found:"
        grep -nE "pkgutil|pkg_resources|__path__.*extend_path|declare_namespace" "$INIT_FILE" | sed 's/^/   /'
        echo ""
        echo "   Solution: Remove these declarations and use PEP 420 implicit namespace packages"
        echo "   See: docs/PEP420_NAMESPACE_MIGRATION.md"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ PASS: No old-style namespace declarations found${NC}"
    fi

    # Check for imports in namespace __init__.py (should be minimal)
    if grep -qE "^from |^import " "$INIT_FILE"; then
        echo -e "${YELLOW}⚠️  WARNING: Import statements found in namespace package __init__.py${NC}"
        echo ""
        echo "   Found imports:"
        grep -nE "^from |^import " "$INIT_FILE" | sed 's/^/   /'
        echo ""
        echo "   Note: Namespace packages should be minimal (docstrings/comments only)"
        echo "   Imports may cause issues with namespace merging across packages"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "${GREEN}✓ PASS: No imports in namespace package __init__.py${NC}"
    fi
fi

# Check 2: pyproject.toml configuration
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Check 2: pyproject.toml namespace configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PYPROJECT="$PROJECT_ROOT/pyproject.toml"

if [ ! -f "$PYPROJECT" ]; then
    echo -e "${RED}❌ FAIL: pyproject.toml not found${NC}"
    ERRORS=$((ERRORS + 1))
else
    if grep -q "namespaces = true" "$PYPROJECT"; then
        echo -e "${GREEN}✓ PASS: 'namespaces = true' found in pyproject.toml${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: 'namespaces = true' not found in [tool.setuptools.packages.find]${NC}"
        echo "   This is required for proper namespace package discovery"
        echo "   Add the following to pyproject.toml:"
        echo ""
        echo "   [tool.setuptools.packages.find]"
        echo "   where = [\"src\"]"
        echo "   include = [\"sage*\"]"
        echo "   namespaces = true  # ← Add this line"
        WARNINGS=$((WARNINGS + 1))
    fi

    if grep -q 'include = \["sage\*"\]' "$PYPROJECT"; then
        echo -e "${GREEN}✓ PASS: Correct package include pattern found${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: 'include = [\"sage*\"]' pattern not found${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check 3: Test actual namespace behavior (if installed)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Check 3: Runtime namespace package behavior"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Try to import and check namespace
python3 << 'EOF'
import sys
import importlib.util

errors = 0
warnings = 0

# Check if sage.benchmark is importable
spec = importlib.util.find_spec("sage.benchmark")
if spec is None:
    print("ℹ️  sage.benchmark not installed (run 'pip install -e .' first)")
    print("   Skipping runtime checks")
else:
    import sage

    # Check if sage is a namespace package
    if hasattr(sage, '__path__') and not hasattr(sage, '__file__'):
        print("✓ PASS: 'sage' is properly configured as a namespace package")
    else:
        print("❌ FAIL: 'sage' is not a proper namespace package")
        errors += 1

    # Check what's in the namespace
    sage_attrs = [attr for attr in dir(sage) if not attr.startswith('_')]
    if sage_attrs:
        print(f"✓ INFO: Found {len(sage_attrs)} subpackage(s) in 'sage' namespace:")
        for attr in sage_attrs:
            print(f"  - sage.{attr}")

    # Try importing sage.benchmark
    try:
        import sage.benchmark
        print("✓ PASS: sage.benchmark successfully imported")
    except ImportError as e:
        print(f"❌ FAIL: Cannot import sage.benchmark: {e}")
        errors += 1

sys.exit(errors)
EOF

RUNTIME_EXIT=$?
if [ $RUNTIME_EXIT -ne 0 ]; then
    ERRORS=$((ERRORS + RUNTIME_EXIT))
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! PEP 420 compliant.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found${NC}"
    echo "   Review warnings above and consider addressing them"
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s) and $WARNINGS warning(s) found${NC}"
    echo ""
    echo "Migration guide: docs/PEP420_NAMESPACE_MIGRATION.md"
    echo "Fix these issues to ensure proper namespace package behavior"
    exit 1
fi
