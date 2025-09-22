#!/bin/bash
# SAGE 安装脚本语法检查工具

echo "🔍 检查所有模块的语法..."

# 检查主脚本
echo "检查主脚本..."
if bash -n quickstart.sh; then
    echo "✅ quickstart.sh 语法正确"
else
    echo "❌ quickstart.sh 语法错误"
    exit 1
fi

# 检查所有模块
for dir in display_tools examination_tools download_tools installation_table; do
    echo "检查 $dir 模块..."
    for file in tools/install/$dir/*.sh; do
        if [ -f "$file" ]; then
            if bash -n "$file"; then
                echo "  ✅ $(basename "$file") 语法正确"
            else
                echo "  ❌ $(basename "$file") 语法错误"
                exit 1
            fi
        fi
    done
done

echo ""
echo "🎉 所有模块语法检查通过！"
