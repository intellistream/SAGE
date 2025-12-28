#!/usr/bin/env bash
# Test pre-commit hook for forbidden patterns

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "🧪 Testing pre-commit hook patterns..."
echo ""

# Create test file with forbidden patterns
TEST_FILE=$(mktemp /tmp/test_forbidden_XXXXXX.py)
trap "rm -f $TEST_FILE" EXIT

cat > "$TEST_FILE" << 'EOF'
# Test file with forbidden patterns

# Pattern 1: sage llm serve
import subprocess
subprocess.run(["sage", "llm", "serve", "-m", "model"])

# Pattern 2: Direct vLLM import
from vllm import LLM
engine = LLM(model="...")

# Pattern 3: vLLM API server
import vllm.entrypoints.openai.api_server

# Pattern 4: Hardcoded port
port = 8001  # LLM port
another_port = 8901  # Benchmark port
EOF

echo "📄 Test file created: $TEST_FILE"
echo ""

# Run hook
if python tools/hooks/check_control_plane_only.py "$TEST_FILE"; then
    echo ""
    echo "❌ FAILED: Hook should have blocked forbidden patterns"
    exit 1
else
    echo ""
    echo "✅ SUCCESS: Hook correctly blocked forbidden patterns"
fi

echo ""
echo "🧪 Testing whitelisted file (should pass)..."

# Create whitelisted file
WHITELIST_FILE=$(mktemp /tmp/test_whitelist_XXXXXX.py)
trap "rm -f $WHITELIST_FILE $TEST_FILE" EXIT

# Use a whitelisted path
mkdir -p /tmp/sage-test/packages/sage-cli/src/sage/cli
WHITELIST_FILE="/tmp/sage-test/packages/sage-cli/src/sage/cli/llm.py"
cat > "$WHITELIST_FILE" << 'EOF'
# Framework internal file - should be whitelisted
from vllm import LLM
EOF

if python tools/hooks/check_control_plane_only.py "$WHITELIST_FILE"; then
    echo "✅ SUCCESS: Whitelisted file passed"
else
    echo "❌ FAILED: Whitelisted file should have passed"
    exit 1
fi

rm -rf /tmp/sage-test

echo ""
echo "✅ All pre-commit hook tests passed!"
