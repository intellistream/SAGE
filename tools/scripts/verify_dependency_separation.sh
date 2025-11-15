#!/bin/bash
# 验证 pyproject.toml 依赖分离改进

set -euo pipefail

echo "🔍 验证 pyproject.toml 依赖分离改进"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}1. 检查所有包的 dependencies 是否不包含 isage-* ...${NC}"
echo ""

has_issues=false

for pkg in packages/*/pyproject.toml; do
    pkg_name=$(basename $(dirname "$pkg"))

    # 跳过 sage meta-package（它的 dependencies 应该包含 isage-*）
    if [[ "$pkg_name" == "sage" ]]; then
        echo -e "${GREEN}✅ $pkg_name: meta-package，dependencies 应该包含 isage-*${NC}"
        continue
    fi

    # 提取 dependencies 部分
    deps=$(sed -n '/^dependencies = \[/,/^\]/p' "$pkg" | grep -E '^\s+"' || true)

    # 检查是否包含 isage-*
    isage_deps=$(echo "$deps" | grep -i 'isage-' || true)

    if [ -n "$isage_deps" ]; then
        echo -e "${YELLOW}⚠️  $pkg_name: dependencies 中仍包含 isage-* 依赖${NC}"
        echo "$isage_deps" | sed 's/^/      /'
        has_issues=true
    else
        echo -e "${GREEN}✅ $pkg_name: dependencies 中无 isage-* 依赖${NC}"
    fi
done

echo ""
echo -e "${BLUE}2. 检查所有包是否添加了 sage-deps ...${NC}"
echo ""

for pkg in packages/*/pyproject.toml; do
    pkg_name=$(basename $(dirname "$pkg"))

    # 跳过不需要 sage-deps 的包
    if [[ "$pkg_name" == "sage-common" || "$pkg_name" == "sage-cli" || "$pkg_name" == "sage" ]]; then
        if [[ "$pkg_name" == "sage" ]]; then
            echo -e "${GREEN}✅ $pkg_name: meta-package，无需 sage-deps${NC}"
        else
            echo -e "${GREEN}✅ $pkg_name: 无需 sage-deps（无内部依赖）${NC}"
        fi
        continue
    fi

    # 检查是否有 sage-deps
    if grep -q "^sage-deps = \[" "$pkg"; then
        echo -e "${GREEN}✅ $pkg_name: 已添加 sage-deps${NC}"
    else
        echo -e "${YELLOW}⚠️  $pkg_name: 未找到 sage-deps${NC}"
        has_issues=true
    fi
done

echo ""
echo -e "${BLUE}3. 检查 sage meta-package 的 extras 是否正确 ...${NC}"
echo ""

sage_toml="packages/sage/pyproject.toml"

# 检查 standard extra 是否使用 [sage-deps]
if grep -q 'isage-apps\[sage-deps\]' "$sage_toml" && \
   grep -q 'isage-benchmark\[sage-deps\]' "$sage_toml" && \
   grep -q 'isage-studio\[sage-deps\]' "$sage_toml" && \
   grep -q 'isage-tools\[sage-deps\]' "$sage_toml"; then
    echo -e "${GREEN}✅ sage meta-package: extras 正确引用 [sage-deps]${NC}"
else
    echo -e "${YELLOW}⚠️  sage meta-package: 某些 extras 未引用 [sage-deps]${NC}"
    has_issues=true
fi

echo ""
echo "========================================"

if [ "$has_issues" = true ]; then
    echo -e "${YELLOW}⚠️  发现一些问题，请检查上述输出${NC}"
    exit 1
else
    echo -e "${GREEN}✅ 所有检查通过！依赖分离改进正确${NC}"
    exit 0
fi
