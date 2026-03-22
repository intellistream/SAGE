#!/bin/bash
# Setup workspace dependencies for SAGE.code-workspace
# This script clones SAGE-Pub.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PARENT_DIR="$(dirname "$SAGE_ROOT")"

echo "🔍 Checking workspace dependencies..."
echo ""

# 1. Check if SAGE-Pub repository exists
echo "📚 Checking SAGE-Pub repository..."
SAGE_PUB_DIR="$PARENT_DIR/SAGE-Pub"
if [ -d "$SAGE_PUB_DIR/.git" ]; then
    echo "✅ SAGE-Pub already exists at: $SAGE_PUB_DIR"
else
    echo "⚠️  SAGE-Pub not found"
    echo ""
    echo "SAGE-Pub contains the documentation for SAGE."
    echo ""
    read -p "Clone SAGE-Pub repository? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "📥 Cloning SAGE-Pub..."
        cd "$PARENT_DIR"
        if git clone git@github.com:intellistream/SAGE-Pub.git; then
            cd SAGE-Pub
            git checkout main-dev
            cd "$SAGE_ROOT"
            echo "✅ SAGE-Pub cloned successfully"
        else
            echo "❌ Failed to clone SAGE-Pub"
            cd "$SAGE_ROOT"
        fi
    else
        echo "⏭️  Skipped. You can safely ignore VS Code warnings about missing folders."
    fi
fi

echo ""
echo "✅ Workspace setup complete!"
echo ""
echo "📁 Workspace folders:"
echo "   • SAGE (main repository)"
if [ -d "$SAGE_PUB_DIR" ]; then
    echo "   • SAGE-Pub (documentation repository)"
fi
echo ""
echo "💡 To open the workspace in VS Code:"
echo "   code SAGE.code-workspace"
