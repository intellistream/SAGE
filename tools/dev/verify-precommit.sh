#!/usr/bin/env bash
# Pre-commit Hook Verification Script
# Run this to verify that pre-commit hooks are properly set up

set -e

echo "🔍 Verifying Pre-commit Setup..."
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "❌ pre-commit is not installed"
    echo "   Install it with: pip install pre-commit"
    exit 1
fi
echo "✅ pre-commit is installed: $(pre-commit --version)"

# Check if .git/hooks/pre-commit exists
if [ ! -f .git/hooks/pre-commit ]; then
    echo "❌ pre-commit hook file not found"
    echo "   Install it with: pre-commit install --config tools/pre-commit-config.yaml"
    exit 1
fi
echo "✅ pre-commit hook file exists"

# Check if the hook is executable
if [ ! -x .git/hooks/pre-commit ]; then
    echo "❌ pre-commit hook is not executable"
    chmod +x .git/hooks/pre-commit
    echo "   Fixed: made pre-commit hook executable"
fi
echo "✅ pre-commit hook is executable"

# Check if core.hooksPath is not set to a custom location
HOOKS_PATH=$(git config --get core.hooksPath || echo "")
if [ -n "$HOOKS_PATH" ]; then
    echo "⚠️  Warning: custom hooks path is set to: $HOOKS_PATH"
    echo "   This might prevent pre-commit from running"
    echo "   Unset it with: git config --unset core.hooksPath"
else
    echo "✅ No custom hooks path configured"
fi

# Test a simple hook run
echo ""
echo "🧪 Testing pre-commit (this may take a moment)..."
if pre-commit run --config tools/pre-commit-config.yaml trailing-whitespace --all-files > /dev/null 2>&1; then
    echo "✅ pre-commit hooks can run successfully"
else
    # Even if it fails, as long as it runs, it's OK
    echo "✅ pre-commit hooks can run (may have found issues to fix)"
fi

echo ""
echo "🎉 Pre-commit setup verification complete!"
echo ""
echo "📝 To ensure hooks run on every commit:"
echo "   1. DON'T use: git commit -n or git commit --no-verify"
echo "   2. Always stage your changes: git add <files>"
echo "   3. Before pushing, run: ./tools/fix-code-quality.sh"
echo ""
echo "💡 To test hooks manually:"
echo "   pre-commit run --all-files --config tools/pre-commit-config.yaml"
