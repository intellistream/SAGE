#!/bin/bash
# 批量升级所有 SAGE 包到 0.2.0
# 将版本管理从中心化改为各包独立管理

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "🔄 升级所有 SAGE 包到 0.2.0..."

# 定义所有需要更新的包
packages=(
    "sage-common"
    "sage-llm-core"
    "sage-platform"
    "sage-kernel"
    "sage-libs"
    "sage-middleware"
    "sage-apps"
    "sage-benchmark"
    "sage-cli"
    "sage-tools"
    "sage-studio"
    "sage-llm-gateway"
    "sage-edge"
    "sage"
)

# 更新每个包的 _version.py 文件
for pkg in "${packages[@]}"; do
    version_file=""

    # 确定版本文件路径
    case "$pkg" in
        "sage-common")
            version_file="packages/sage-common/src/sage/common/_version.py"
            ;;
        "sage-llm-core")
            version_file="packages/sage-llm-core/src/sage/llm/_version.py"
            ;;
        "sage-platform")
            version_file="packages/sage-platform/src/sage/platform/_version.py"
            ;;
        "sage-kernel")
            version_file="packages/sage-kernel/src/sage/kernel/_version.py"
            ;;
        "sage-libs")
            version_file="packages/sage-libs/src/sage/libs/_version.py"
            ;;
        "sage-middleware")
            version_file="packages/sage-middleware/src/sage/middleware/_version.py"
            ;;
        "sage-apps")
            version_file="packages/sage-apps/src/sage/apps/_version.py"
            ;;
        "sage-benchmark")
            version_file="packages/sage-benchmark/src/sage/benchmark/_version.py"
            ;;
        "sage-cli")
            version_file="packages/sage-cli/src/sage/cli/_version.py"
            ;;
        "sage-tools")
            version_file="packages/sage-tools/src/sage/tools/_version.py"
            ;;
        "sage-studio")
            version_file="packages/sage-studio/src/sage/studio/_version.py"
            ;;
        "sage-llm-gateway")
            version_file="packages/sage-llm-gateway/src/sage/llm/gateway/_version.py"
            ;;
        "sage-edge")
            version_file="packages/sage-edge/src/sage/edge/_version.py"
            ;;
        "sage")
            version_file="packages/sage/src/sage/_version.py"
            ;;
    esac

    if [ -n "$version_file" ] && [ -f "$version_file" ]; then
        echo "  📝 更新 $pkg: $version_file"

        # 使用 sed 更新版本号（支持多种版本格式）
        sed -i 's/__version__ = "0\.1\.10\.7"/__version__ = "0.2.0"/' "$version_file"
        sed -i 's/__version__ = "0\.1\.0"/__version__ = "0.2.0"/' "$version_file"
        sed -i 's/__version__ = "0\.1\.[0-9]\+"/__version__ = "0.2.0"/' "$version_file"

        # 验证更新
        if grep -q '__version__ = "0.2.0"' "$version_file"; then
            echo "     ✅ $pkg 版本已更新到 0.2.0"
        else
            echo "     ⚠️  $pkg 版本文件格式可能不标准，请手动检查"
        fi
    else
        echo "  ⚠️  未找到 $pkg 的版本文件: $version_file"
    fi
done

echo ""
echo "🔧 移除中心化版本依赖..."
echo ""

# 修复各包的 sage/__init__.py，使其不再依赖 sage.common._version
namespace_init_files=(
    "packages/sage-kernel/src/sage/__init__.py"
    "packages/sage-libs/src/sage/__init__.py"
    "packages/sage-platform/src/sage/__init__.py"
    "packages/sage-benchmark/src/sage/__init__.py"
    "packages/sage-studio/src/sage/__init__.py"
    "packages/sage-tools/src/sage/__init__.py"
    "packages/sage-middleware/src/sage/__init__.py"
    "packages/sage-apps/src/sage/__init__.py"
    "packages/sage-cli/src/sage/__init__.py"
)

for init_file in "${namespace_init_files[@]}"; do
    if [ -f "$init_file" ]; then
        echo "  🔧 修复 $init_file..."

        # 将 sage.common._version 导入改为尝试导入但不强制依赖
        # 这样即使 sage-common 不在，命名空间包也能工作
        sed -i 's/from sage\.common\._version import/__version__ = "unknown"; __author__ = "IntelliStream Team"; __email__ = "shuhao_zhang@hust.edu.cn"  # from sage.common._version import/' "$init_file"

        echo "     ✅ 已修复"
    fi
done

echo ""
echo "✅ 版本更新完成！"
echo ""
echo "📋 验证更新结果："
echo ""

# 验证所有版本文件
for pkg in "${packages[@]}"; do
    version_file=""

    case "$pkg" in
        "sage-common") version_file="packages/sage-common/src/sage/common/_version.py" ;;
        "sage-llm-core") version_file="packages/sage-llm-core/src/sage/llm/_version.py" ;;
        "sage-platform") version_file="packages/sage-platform/src/sage/platform/_version.py" ;;
        "sage-kernel") version_file="packages/sage-kernel/src/sage/kernel/_version.py" ;;
        "sage-libs") version_file="packages/sage-libs/src/sage/libs/_version.py" ;;
        "sage-middleware") version_file="packages/sage-middleware/src/sage/middleware/_version.py" ;;
        "sage-apps") version_file="packages/sage-apps/src/sage/apps/_version.py" ;;
        "sage-benchmark") version_file="packages/sage-benchmark/src/sage/benchmark/_version.py" ;;
        "sage-cli") version_file="packages/sage-cli/src/sage/cli/_version.py" ;;
        "sage-tools") version_file="packages/sage-tools/src/sage/tools/_version.py" ;;
        "sage-studio") version_file="packages/sage-studio/src/sage/studio/_version.py" ;;
        "sage-llm-gateway") version_file="packages/sage-llm-gateway/src/sage/llm/gateway/_version.py" ;;
        "sage-edge") version_file="packages/sage-edge/src/sage/edge/_version.py" ;;
        "sage") version_file="packages/sage/src/sage/_version.py" ;;
    esac

    if [ -f "$version_file" ]; then
        version=$(grep '__version__' "$version_file" | head -1)
        printf "  %-20s %s\n" "$pkg:" "$version"
    fi
done

echo ""
echo "🎯 下一步："
echo "  1. 提交这些更改: git add -A && git commit -m 'chore: upgrade all packages to 0.2.0'"
echo "  2. 重新安装: ./quickstart.sh --dev --yes"
echo ""
