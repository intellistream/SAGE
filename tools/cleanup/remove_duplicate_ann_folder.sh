#!/usr/bin/env bash
# Remove duplicate ann/ folder (keep anns/)
# The ann/ folder is an incomplete legacy implementation that should be removed.
# All functionality is in anns/ which is the canonical location.

set -euo pipefail

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ANN_DIR="${SAGE_ROOT}/packages/sage-libs/src/sage/libs/ann"

echo "🔍 Checking for duplicate ann/ folder..."

if [ ! -d "$ANN_DIR" ]; then
    echo "✅ ann/ folder already removed"
    exit 0
fi

echo "📋 Contents of ann/ folder:"
find "$ANN_DIR" -type f

echo ""
echo "⚠️  About to remove: $ANN_DIR"
echo "    Reason: Incomplete legacy implementation, superseded by anns/"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo "🗑️  Removing ann/ folder..."
rm -rf "$ANN_DIR"

echo "✅ Successfully removed duplicate ann/ folder"
echo "✅ Please use 'from sage.libs.anns import ...' going forward"
