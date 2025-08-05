#!/bin/bash
# 商业内容安全检查脚本
# 用于确保上传前不包含商业/闭源内容

echo "🔍 SAGE 商业内容安全检查"
echo "=========================="

# 检查标志
HAS_COMMERCIAL=0

# 1. 检查requirements文件中的商业引用
echo "📋 检查 requirements 文件..."
if grep -r "commercial" requirements*.txt 2>/dev/null; then
    echo "❌ 发现requirements文件包含商业引用!"
    HAS_COMMERCIAL=1
else
    echo "✅ requirements文件安全"
fi

# 2. 检查是否存在商业requirements文件
if [ -f "requirements-commercial.txt" ]; then
    echo "❌ 发现商业requirements文件 requirements-commercial.txt"
    echo "   这个文件不应该在git仓库中!"
    HAS_COMMERCIAL=1
else
    echo "✅ 无商业requirements文件"
fi

# 3. 检查是否存在商业目录
if [ -d "packages/commercial" ]; then
    echo "❌ 发现商业目录 packages/commercial/"
    echo "   这个目录不应该在git仓库中!"
    HAS_COMMERCIAL=1
else
    echo "✅ 无商业目录"
fi

# 4. 检查git状态中的商业文件
echo "📂 检查Git状态..."
if git status --porcelain | grep -E "(commercial|Commercial)"; then
    echo "❌ Git状态中发现商业文件!"
    HAS_COMMERCIAL=1
else
    echo "✅ Git状态安全"
fi

# 5. 检查.gitignore是否包含保护规则
echo "🛡️  检查.gitignore保护..."
if grep -q "commercial" .gitignore && grep -q "requirements-commercial.txt" .gitignore; then
    echo "✅ .gitignore包含商业保护规则"
else
    echo "⚠️  .gitignore缺少商业保护规则"
    echo "   建议添加:"
    echo "   requirements-commercial.txt"
    echo "   packages/commercial/"
fi

# 总结
echo ""
echo "🎯 检查结果:"
if [ $HAS_COMMERCIAL -eq 0 ]; then
    echo "✅ 安全! 可以上传到PyPI和公共仓库"
    echo "🚀 开源版本准备就绪"
    exit 0
else
    echo "❌ 危险! 发现商业内容"
    echo "🔒 请先清理商业内容再上传"
    echo ""
    echo "💡 修复建议:"
    echo "   1. 删除或移动 requirements-commercial.txt"
    echo "   2. 删除或移动 packages/commercial/"
    echo "   3. 检查git add的文件"
    echo "   4. 确保.gitignore包含保护规则"
    exit 1
fi
