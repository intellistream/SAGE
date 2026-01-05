#!/bin/bash
# Bump versions for all packages affected by PEP 420 migration
# Usage: ./tools/scripts/bump_versions_pep420.sh

set -e

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

echo "🔢 批量递增版本号（PEP 420 迁移发布）"
echo "========================================="

# Define packages and their version increments
# Strategy: Unified 4-digit versioning (X.Y.Z.W) for all packages
# - 0.2.3 → 0.2.3.0 (normalize to 4 digits)
# - 0.2.3.0 → 0.2.3.1 (increment patch)
declare -A VERSION_UPDATES=(
    ["packages/sage/src/sage/_version.py"]="0.2.2→0.2.2.0"
    ["packages/sage-common/src/sage/common/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-llm-core/src/sage/llm/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-platform/src/sage/platform/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-kernel/src/sage/kernel/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-libs/src/sage/libs/_version.py"]="0.2.0.6→0.2.0.7"
    ["packages/sage-middleware/src/sage/middleware/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-apps/src/sage/apps/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-cli/src/sage/cli/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-studio/src/sage/studio/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-llm-gateway/src/sage/llm/gateway/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-edge/src/sage/edge/_version.py"]="0.2.3→0.2.3.0"
    ["packages/sage-tools/src/sage/tools/_version.py"]="0.2.3→0.2.3.0"
)

# Perform version updates
for file in "${!VERSION_UPDATES[@]}"; do
    version_change="${VERSION_UPDATES[$file]}"
    old_version="${version_change%%→*}"
    new_version="${version_change##*→}"

    if [ ! -f "$file" ]; then
        echo "⚠️  文件不存在: $file"
        continue
    fi

    # Check current version
    current=$(grep -oP '__version__ = "\K[^"]+' "$file" || echo "unknown")
    if [ "$current" != "$old_version" ]; then
        echo "⚠️  版本不匹配: $file"
        echo "   预期: $old_version"
        echo "   实际: $current"
        echo "   跳过此包..."
        continue
    fi

    # Update version
    sed -i "s/__version__ = \"$old_version\"/__version__ = \"$new_version\"/" "$file"
    echo "✅ $file: $old_version → $new_version"
done

echo ""
echo "✅ 所有版本号递增完成！"
echo ""
echo "📋 版本号策略: 统一使用 4 位版本号 (X.Y.Z.W)"
echo "   - 11 个包从 0.2.3 规范化为 0.2.3.0"
echo "   - sage-libs 从 0.2.0.6 递增为 0.2.0.7"
echo "   - sage 元包从 0.2.2 规范化为 0.2.2.0"
echo ""
echo "📋 下一步操作:"
echo "   1. 提交版本变更: git add packages/*/src/sage/*/_version.py && git commit -m 'chore: normalize versions to 4-digit format for PEP 420 release'"
echo "   2. 推送到 GitHub: git push origin main-dev"
echo "   3. 使用 sage-pypi-publisher 发布所有包"
