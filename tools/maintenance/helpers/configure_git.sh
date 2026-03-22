#!/bin/bash
# Git configuration helper for the SAGE repository.

set -e

echo "🔧 Configuring Git settings for SAGE repository..."

git config diff.renameLimit 10000
echo "✅ Set diff.renameLimit to 10000"

git config merge.renameLimit 10000
echo "✅ Set merge.renameLimit to 10000"

git config core.preloadindex true
echo "✅ Enabled core.preloadindex"

git config pack.threads 0
echo "✅ Set pack.threads to auto"

if git config --get-all core.fsmonitor &>/dev/null || command -v watchman &>/dev/null; then
    git config core.fsmonitor true
    echo "✅ Enabled core.fsmonitor"
else
    echo "ℹ️  Watchman not found, skipping fsmonitor (optional optimization)"
fi

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