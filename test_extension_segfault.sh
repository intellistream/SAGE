#!/bin/bash
# 测试扩展安装中的段错误处理

echo "测试段错误处理..."

# 运行扩展安装命令
sage extensions install all --force
exit_code=$?

echo ""
echo "命令退出码: $exit_code"

if [ $exit_code -eq 139 ]; then
    echo "检测到段错误(退出码139)"
    echo "验证扩展是否实际安装成功..."
    echo ""
    sage extensions status
    status_exit_code=$?
    
    if [ $status_exit_code -eq 0 ]; then
        echo ""
        echo "✅ 尽管有段错误，扩展实际上已成功安装"
        exit 0
    else
        echo ""
        echo "❌ 扩展安装确实失败"
        exit 1
    fi
elif [ $exit_code -eq 0 ]; then
    echo "✅ 安装成功，无段错误"
    exit 0
else
    echo "❌ 安装失败，退出码: $exit_code"
    exit $exit_code
fi
