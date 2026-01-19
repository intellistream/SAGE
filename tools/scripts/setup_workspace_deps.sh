#!/bin/bash
# Setup workspace dependencies for SAGE.code-workspace
# This script clones SAGE-Pub and optionally sage-team-info repositories

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
        if git clone https://github.com/intellistream/SAGE-Pub.git; then
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

# 2. Check if sage-team-info exists
echo "👥 Checking sage-team-info (optional)..."
TEAM_INFO_DIR="$PARENT_DIR/sage-team-info"
if [ -d "$TEAM_INFO_DIR" ]; then
    echo "✅ sage-team-info already exists at: $TEAM_INFO_DIR"
else
    echo "⚠️  sage-team-info not found"
    echo ""
    echo "The SAGE.code-workspace includes sage-team-info for team members."
    echo "If you're a core team member, you can clone it now."
    echo ""
    read -p "Clone sage-team-info? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📥 Cloning sage-team-info..."
        cd "$PARENT_DIR"
        if git clone https://github.com/intellistream/sage-team-info.git; then
            echo "✅ sage-team-info cloned successfully"
        else
            echo "❌ Failed to clone. You may not have access to this private repository."
            echo "   This is normal if you're not a core team member."
        fi
        cd "$SAGE_ROOT"
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
if [ -d "$TEAM_INFO_DIR" ]; then
    echo "   • sage-team-info (team documentation)"
fi
echo ""
echo "💡 To open the workspace in VS Code:"
echo "   code SAGE.code-workspace"
