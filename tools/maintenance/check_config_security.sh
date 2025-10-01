#!/bin/bash
# 配置文件安全检查脚本
# 用于检测配置文件中可能泄露的 API keys

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_DIR="$REPO_ROOT/examples/config"

echo "🔍 检查配置文件中的敏感信息..."
echo "配置目录: $CONFIG_DIR"
echo ""

FOUND_ISSUES=0

# 检查 sk- 开头的 API keys (OpenAI/DashScope 格式)
echo "1. 检查 sk- 开头的真实 API keys..."
if grep -rE 'api_key.*"sk-[a-zA-Z0-9]{32,}"' "$CONFIG_DIR"/*.yaml 2>/dev/null; then
    echo "❌ 发现真实的 API keys (sk- 开头)"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
    echo "✅ 未发现 sk- 开头的 API keys"
fi
echo ""

# 检查长字符串的 API keys (超过 20 个字符的非空值)
echo "2. 检查可疑的长字符串 API keys..."
if grep -rE 'api_key:.*"[a-zA-Z0-9_-]{20,}"' "$CONFIG_DIR"/*.yaml 2>/dev/null | grep -v '""' | grep -v 'your_' | grep -v 'OPENAI_API_KEY'; then
    echo "❌ 发现可疑的长字符串 API keys"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
    echo "✅ 未发现可疑的长字符串"
fi
echo ""

# 检查测试 token
echo "3. 检查测试 token (token-abc123)..."
if grep -rE 'token-abc123' "$CONFIG_DIR"/*.yaml 2>/dev/null; then
    echo "❌ 发现测试 token，应该替换为空字符串"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
    echo "✅ 未发现测试 token"
fi
echo ""

# 检查环境变量引用格式
echo "4. 检查环境变量引用格式..."
if grep -rE '\$\{[A-Z_]+\}' "$CONFIG_DIR"/*.yaml 2>/dev/null; then
    echo "⚠️  发现环境变量引用格式 \${VAR}，这在 YAML 中不会自动展开"
    echo "   建议使用空字符串 '' 并让代码从环境变量读取"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
else
    echo "✅ 未发现需要调整的环境变量引用"
fi
echo ""

# 检查 .env 文件是否在 .gitignore 中
echo "5. 检查 .env 是否在 .gitignore 中..."
if grep -q "^/.env$\|^.env$" "$REPO_ROOT/.gitignore" 2>/dev/null; then
    echo "✅ .env 文件已在 .gitignore 中"
else
    echo "❌ .env 文件未在 .gitignore 中！"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
fi
echo ""

# 检查 .env.template 是否存在
echo "6. 检查 .env.template 文件..."
if [ -f "$REPO_ROOT/.env.template" ]; then
    echo "✅ .env.template 文件存在"
else
    echo "⚠️  .env.template 文件不存在"
fi
echo ""

# 总结
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FOUND_ISSUES -eq 0 ]; then
    echo "✅ 安全检查通过！未发现敏感信息泄露"
    exit 0
else
    echo "❌ 发现 $FOUND_ISSUES 个安全问题，请修复后再提交代码"
    exit 1
fi
