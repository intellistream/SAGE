#!/bin/bash
# Git configuration script for SAGE repository
# This script sets recommended Git configurations for working with large repos

set -e

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "🔧 Configuring Git settings for SAGE repository..."

# Set diff.renameLimit to handle large file renames
# Default is 400, which is too low for SAGE
git config diff.renameLimit 10000
echo "✅ Set diff.renameLimit to 10000"

# Set merge.renameLimit for merge operations
git config merge.renameLimit 10000
echo "✅ Set merge.renameLimit to 10000"

# Enable parallel index preload for better performance
git config core.preloadindex true
echo "✅ Enabled core.preloadindex"

# Use multiple threads for pack operations (speeds up fetch/push)
git config pack.threads 0  # 0 = auto-detect CPU cores
echo "✅ Set pack.threads to auto"

# Enable filesystem monitor for better performance (if available)
if git config --get-all core.fsmonitor &>/dev/null || command -v watchman &>/dev/null; then
    git config core.fsmonitor true
    echo "✅ Enabled core.fsmonitor"
else
    echo "ℹ️  Watchman not found, skipping fsmonitor (optional optimization)"
fi

# Configure credential caching (15 minutes)
git config credential.helper 'cache --timeout=900'
echo "✅ Set credential cache timeout to 15 minutes"

echo ""
echo "✅ Git configuration complete!"
echo ""
echo "📋 Current settings:"
echo "   diff.renameLimit: $(git config diff.renameLimit)"
echo "   merge.renameLimit: $(git config merge.renameLimit)"
echo "   core.preloadindex: $(git config core.preloadindex)"
echo "   pack.threads: $(git config pack.threads)"
echo ""
