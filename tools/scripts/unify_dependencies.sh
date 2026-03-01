#!/bin/bash
# 统一 SAGE 所有包的依赖版本
#
# 原则：
# 1. L1 (sage-common, sage-llm-core) 定义基础依赖
# 2. 其他包继承 L1 的版本约束

set -e

echo "🔧 统一 SAGE 依赖版本..."
echo ""

# 定义统一的版本约束
declare -A UNIFIED_DEPS=(
    # 核心计算库
    ["torch"]='>=2.7.0,<3.0.0'
    ["torchvision"]='>=0.22.0,<1.0.0'
    ["numpy"]='>=1.26.0,<2.3.0'

    # Transformers 生态
    ["transformers"]='>=4.52.0,<4.58.0'
    ["tokenizers"]='>=0.21.0,<0.24.0'
    ["accelerate"]='>=1.9.0,<2.0.0'
    ["peft"]='>=0.18.0,<1.0.0'
    ["huggingface-hub"]='>=0.34.0,<1.0.0'

    # Web 框架
    ["fastapi"]='>=0.115.0,<1.0.0'
    ["uvicorn"]='>=0.34.0,<1.0.0'
    ["pydantic"]='>=2.10.0,<3.0.0'
    ["pydantic-settings"]='>=2.0.0'

    # HTTP 客户端
    ["requests"]='>=2.32.0,<3.0.0'
    ["httpx"]='>=0.28.0,<1.0.0'

    # 其他常用库
    ["pyyaml"]='>=6.0'
    ["python-dotenv"]='>=1.1.0,<2.0.0'
    ["rich"]='>=13.0.0,<14.0.0'
    ["typer"]='>=0.15.0,<1.0.0'
    ["click"]='>=8.0.0,<9.0.0'
)

# 需要修复的包和依赖
declare -A FIXES=(
    # sage-common: torch 版本过低
    ["packages/sage-common/pyproject.toml:torch"]='torch>=2.4.0|torch>=2.7.0,<3.0.0'

    # sage-kernel: fastapi 版本不一致
    ["packages/sage-kernel/pyproject.toml:fastapi1"]='fastapi>=0.100.0|fastapi>=0.115.0,<1.0.0'

    # sage-tools: fastapi 版本太严格
    ["packages/sage-tools/pyproject.toml:fastapi"]='fastapi>=0.115,<0.116|fastapi>=0.115.0,<1.0.0'

    # sage-apps: transformers 版本不一致
    ["packages/sage-apps/pyproject.toml:transformers"]='transformers>=4.52.0,<4.56.0|transformers>=4.52.0,<4.58.0'
)

# 统计
fixed_count=0
total_count=${#FIXES[@]}

echo "📋 需要修复 $total_count 个依赖不一致问题："
echo ""

for key in "${!FIXES[@]}"; do
    IFS=':' read -r file dep <<< "$key"
    IFS='|' read -r old_ver new_ver <<< "${FIXES[$key]}"

    echo "  📝 $file"
    echo "     $dep: $old_ver → $new_ver"

    if [ -f "$file" ]; then
        # 使用 sed 替换（需要转义特殊字符）
        old_escaped=$(echo "$old_ver" | sed 's/[.[\*^$()+?{|]/\\&/g')
        new_escaped=$(echo "$new_ver" | sed 's/[&/]/\\&/g')

        # 替换
        sed -i "s/\"$old_escaped\"/\"$new_escaped\"/g" "$file"

        # 验证替换是否成功
        if grep -q "$new_ver" "$file"; then
            echo "     ✅ 已修复"
            ((fixed_count++))
        else
            echo "     ⚠️  替换可能失败，请手动检查"
        fi
    else
        echo "     ❌ 文件不存在"
    fi
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 修复完成: $fixed_count/$total_count"
echo ""
echo "💡 后续步骤:"
echo "  1. 运行测试: sage-dev project test"
echo "  2. 提交更改: git add packages/*/pyproject.toml"
echo "  3. 创建 PR"
echo ""
