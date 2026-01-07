#!/bin/bash
# Publish all SAGE packages to PyPI after PEP 420 migration
# Usage: ./tools/scripts/publish_pep420_release.sh [--test-pypi] [--dry-run]

set -e

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

# Parse arguments
REPOSITORY="pypi"
DRY_RUN="--no-dry-run"

for arg in "$@"; do
    case $arg in
        --test-pypi)
            REPOSITORY="testpypi"
            shift
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --help)
            echo "Usage: $0 [--test-pypi] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --test-pypi   Upload to TestPyPI instead of PyPI"
            echo "  --dry-run     Perform a dry run without actual upload"
            echo "  --help        Show this help message"
            exit 0
            ;;
    esac
done

echo "🚀 SAGE PEP 420 Migration - PyPI 发布"
echo "========================================"
echo "Repository: $REPOSITORY"
echo "Dry run: $DRY_RUN"
echo ""

# Define packages in dependency order (L1 → L6)
# L1: Foundation packages
declare -a L1_PACKAGES=(
    "packages/sage-common"
    "packages/sage-llm-core"
)

# L2: Platform services
declare -a L2_PACKAGES=(
    "packages/sage-platform"
)

# L3: Kernel & Libs
declare -a L3_PACKAGES=(
    "packages/sage-kernel"
    "packages/sage-libs"
)

# L4: Middleware
declare -a L4_PACKAGES=(
    "packages/sage-middleware"
)

# L5: Apps
declare -a L5_PACKAGES=(
    "packages/sage-apps"
)

# L6: Interface layer
declare -a L6_PACKAGES=(
    "packages/sage-cli"
    "packages/sage-studio"
    "packages/sage-tools"
    "packages/sage-llm-gateway"
    "    # "packages/sage-edge"  # 已独立: https://github.com/intellistream/sage-edge"
)

# Meta-package
declare -a META_PACKAGE=(
    "packages/sage"
)

# Combine all packages in order
ALL_PACKAGES=(
    "${L1_PACKAGES[@]}"
    "${L2_PACKAGES[@]}"
    "${L3_PACKAGES[@]}"
    "${L4_PACKAGES[@]}"
    "${L5_PACKAGES[@]}"
    "${L6_PACKAGES[@]}"
    "${META_PACKAGE[@]}"
)

echo "📦 将按以下顺序发布 ${#ALL_PACKAGES[@]} 个包:"
echo ""
for i in "${!ALL_PACKAGES[@]}"; do
    pkg="${ALL_PACKAGES[$i]}"
    pkg_name=$(basename "$pkg")
    # Find version from _version.py
    version=$(find "$pkg/src" -name "_version.py" -type f ! -path "*/pybind11/*" -exec grep -oP '__version__ = "\K[^"]+' {} \; 2>/dev/null | head -1)
    [ -z "$version" ] && version="unknown"
    printf "  %2d. %-25s (v%s)\n" $((i+1)) "$pkg_name" "$version"
done
echo ""

# Confirm before proceeding
if [ "$DRY_RUN" = "--no-dry-run" ]; then
    read -p "⚠️  确认发布到 $REPOSITORY? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ 已取消发布"
        exit 0
    fi
fi

echo ""
echo "🔨 开始构建和发布..."
echo ""

SUCCESS_COUNT=0
FAILED_PACKAGES=()

for pkg_path in "${ALL_PACKAGES[@]}"; do
    pkg_name=$(basename "$pkg_path")
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 处理: $pkg_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Build and upload using sage-pypi-publisher
    if sage-pypi-publisher build "$pkg_path" \
        --upload \
        --repository "$REPOSITORY" \
        $DRY_RUN; then
        echo "✅ $pkg_name 发布成功"
        ((SUCCESS_COUNT++))
    else
        echo "❌ $pkg_name 发布失败"
        FAILED_PACKAGES+=("$pkg_name")
    fi

    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 发布总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 成功: $SUCCESS_COUNT/${#ALL_PACKAGES[@]}"
if [ ${#FAILED_PACKAGES[@]} -gt 0 ]; then
    echo "❌ 失败: ${#FAILED_PACKAGES[@]}"
    echo ""
    echo "失败的包:"
    for pkg in "${FAILED_PACKAGES[@]}"; do
        echo "  - $pkg"
    done
    exit 1
else
    echo "🎉 所有包发布成功！"
fi

echo ""
echo "📋 验证安装:"
echo "  pip install --upgrade sage  # 安装元包（包含所有子包）"
echo ""
echo "📖 查看 PyPI 页面:"
echo "  https://pypi.org/project/sage/"
