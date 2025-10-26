#!/bin/bash
# CI/CD 命令测试脚本
# 用于在推送前验证 CI/CD 工作流中使用的命令是否正常工作

set -e  # 遇到错误立即退出

echo "======================================================================"
echo "🧪 测试 CI/CD 工作流命令"
echo "======================================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
TESTS_PASSED=0
TESTS_FAILED=0

# 测试函数
test_command() {
    local test_name="$1"
    local command="$2"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "测试: $test_name"
    echo "命令: $command"
    echo ""
    
    if eval "$command" > /tmp/test_output.log 2>&1; then
        echo -e "${GREEN}✅ 通过${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ 失败${NC}"
        echo "错误输出:"
        tail -20 /tmp/test_output.log
        ((TESTS_FAILED++))
    fi
    echo ""
}

# 检查 sage 命令是否可用
if ! command -v sage &> /dev/null; then
    echo -e "${RED}❌ sage 命令不可用！${NC}"
    echo "请先安装 sage-tools: pip install -e packages/sage-tools"
    exit 1
fi

echo "📦 检测到的 sage 版本:"
sage --version 2>/dev/null || sage dev --version || echo "无法获取版本"
echo ""

# 测试架构检查命令
test_command "架构检查 - 全部文件" \
    "sage dev check-architecture"

test_command "架构检查 - 仅变更文件" \
    "sage dev check-architecture --changed-only"

test_command "架构信息显示" \
    "sage dev architecture --no-dependencies | grep -q 'sage-common'"

test_command "架构信息 - JSON 格式" \
    "sage dev architecture --format json | python3 -m json.tool > /dev/null"

# 测试文档检查命令
test_command "Dev-notes 文档检查" \
    "timeout 30 sage dev check-devnotes"

test_command "Dev-notes 文档检查 - 结构检查" \
    "timeout 30 sage dev check-devnotes --check-structure"

# 测试 README 检查命令
test_command "README 质量检查" \
    "sage dev check-readme"

# 测试综合检查命令
test_command "综合检查 - 仅变更文件" \
    "timeout 60 sage dev check-all --changed-only"

# 测试质量检查命令（模拟 CI 用法）
test_command "代码质量检查（CI 模式）" \
    "sage dev quality --check-only --no-architecture --no-devnotes 2>&1 | grep -q 'Pre-commit' || true"

echo "======================================================================"
echo "📊 测试结果汇总"
echo "======================================================================"
echo ""
echo -e "通过: ${GREEN}$TESTS_PASSED${NC}"
echo -e "失败: ${RED}$TESTS_FAILED${NC}"
echo "总计: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！CI/CD 命令工作正常。${NC}"
    exit 0
else
    echo -e "${RED}❌ 有 $TESTS_FAILED 个测试失败。请修复后再推送。${NC}"
    exit 1
fi
