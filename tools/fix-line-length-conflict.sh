#!/bin/bash
# 统一所有包的 Black/isort 行长度配置为 100
# 解决 pre-commit 和 Pylance 的行长度冲突

set -e

echo "🔧 修复 pre-commit 和 Pylance 的行长度冲突..."
echo ""

PACKAGES=(
    "packages/sage-libs"
    "packages/sage-kernel"
    "packages/sage-common"
    "packages/sage-middleware"
    "packages/sage-tools"
    "packages/sage-studio"
    "packages/sage"
    "packages/sage-platform"
)

for pkg in "${PACKAGES[@]}"; do
    toml_file="$pkg/pyproject.toml"
    if [ -f "$toml_file" ]; then
        echo "📝 更新 $toml_file"
        
        # 更新 Black line-length
        sed -i 's/^line-length = 88$/line-length = 100/' "$toml_file"
        
        # 更新 isort line_length
        sed -i 's/^line_length = 88$/line_length = 100/' "$toml_file"
        
        # 更新 Ruff line-length
        sed -i 's/^line-length = 88$/line-length = 100/' "$toml_file"
    fi
done

echo ""
echo "✅ 完成！所有包的行长度已统一为 100"
echo ""
echo "📌 下一步："
echo "   1. 运行: pre-commit run --all-files --config tools/pre-commit-config.yaml"
echo "   2. 检查 Pylance 错误是否减少"
echo "   3. 提交更改"
