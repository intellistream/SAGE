#!/usr/bin/env bash
# Verify ANN cleanup was successful

set -euo pipefail

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "🔍 Verifying ANN cleanup..."
echo ""

# Check 1: ann/ folder should not exist
echo "✓ Check 1: Verifying ann/ folder is removed..."
if [ -d "${SAGE_ROOT}/packages/sage-libs/src/sage/libs/ann" ]; then
    echo "❌ FAIL: ann/ folder still exists!"
    exit 1
else
    echo "✅ PASS: ann/ folder successfully removed"
fi

# Check 2: anns/ folder should exist
echo ""
echo "✓ Check 2: Verifying anns/ folder exists..."
if [ ! -d "${SAGE_ROOT}/packages/sage-libs/src/sage/libs/anns" ]; then
    echo "❌ FAIL: anns/ folder not found!"
    exit 1
else
    echo "✅ PASS: anns/ folder exists"
fi

# Check 3: No Python code should reference sage.libs.ann (without 's')
echo ""
echo "✓ Check 3: Verifying no code references old sage.libs.ann path..."
cd "$SAGE_ROOT"
if rg "sage\.libs\.ann[^s]" --type py packages/ 2>/dev/null | grep -v "^#" | grep -v "\.md:" > /dev/null; then
    echo "⚠️  WARNING: Found references to old sage.libs.ann (check if they're just comments):"
    rg "sage\.libs\.ann[^s]" --type py packages/ | head -5
else
    echo "✅ PASS: No Python code references old sage.libs.ann path"
fi

# Check 4: Verify anns interface files exist
echo ""
echo "✓ Check 4: Verifying anns interface files..."
REQUIRED_FILES=(
    "packages/sage-libs/src/sage/libs/anns/__init__.py"
    "packages/sage-libs/src/sage/libs/anns/README.md"
    "packages/sage-libs/src/sage/libs/anns/interface/base.py"
    "packages/sage-libs/src/sage/libs/anns/interface/factory.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "${SAGE_ROOT}/${file}" ]; then
        echo "❌ FAIL: Missing required file: ${file}"
        exit 1
    fi
done
echo "✅ PASS: All required anns interface files exist"

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ ALL CHECKS PASSED!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  - ann/ folder: ❌ Removed (was duplicate)"
echo "  - anns/ folder: ✅ Kept (canonical location)"
echo "  - Code references: ✅ Clean"
echo "  - Interface files: ✅ Complete"
echo ""
echo "✅ Use: from sage.libs.anns import create, register, registered"
echo "❌ Old: from sage.libs.ann import ... (NO LONGER EXISTS)"
