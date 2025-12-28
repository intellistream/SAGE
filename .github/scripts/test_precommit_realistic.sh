#!/usr/bin/env bash
# Realistic test of pre-commit hook with git staging

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "🧪 Testing pre-commit hook with git staging..."
echo ""

# Create a test file with forbidden pattern
TEST_FILE="test_forbidden_pattern_tmp.py"
cat > "$TEST_FILE" << 'EOF'
# This file tests pre-commit hook
from vllm import LLM  # This should be caught
engine = LLM(model="test")
EOF

echo "📄 Created test file: $TEST_FILE"
echo ""

# Stage the file
git add "$TEST_FILE" 2>/dev/null || true

echo "🔍 Running pre-commit hook..."
if python tools/hooks/check_control_plane_only.py; then
    echo "❌ FAILED: Hook should have caught forbidden pattern"
    git reset HEAD "$TEST_FILE" 2>/dev/null || true
    rm -f "$TEST_FILE"
    exit 1
else
    echo "✅ SUCCESS: Hook correctly caught forbidden pattern!"
fi

# Clean up
git reset HEAD "$TEST_FILE" 2>/dev/null || true
rm -f "$TEST_FILE"

echo ""
echo "✅ Pre-commit hook test passed!"
