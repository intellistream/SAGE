#!/bin/bash
# 运行所有 SAGE 安装工具测试
# 用法: bash run_all_tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 导入颜色定义
source "$SAGE_ROOT/tools/install/display_tools/colors.sh"

# 测试统计
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║                                                ║"
echo "║   🧪 SAGE 测试套件 - 完整测试运行              ║"
echo "║                                                ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

run_test_suite() {
    local test_file="$1"
    local test_name="$2"

    TOTAL_SUITES=$((TOTAL_SUITES + 1))

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}运行测试套件: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if bash "$test_file"; then
        echo ""
        echo -e "${GREEN}✅ $test_name 通过${NC}"
        PASSED_SUITES=$((PASSED_SUITES + 1))
        return 0
    else
        echo ""
        echo -e "${RED}❌ $test_name 失败${NC}"
        FAILED_SUITES=$((FAILED_SUITES + 1))
        return 1
    fi
}

# 运行所有测试套件
run_test_suite "$SCRIPT_DIR/test_environment_config.sh" "环境配置单元测试"
run_test_suite "$SCRIPT_DIR/test_cleanup_tools.sh" "清理工具单元测试"
run_test_suite "$SCRIPT_DIR/test_e2e_integration.sh" "端到端集成测试"

# 打印总结
echo ""
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                ║${NC}"
echo -e "${BLUE}║              🎯 测试运行总结                    ║${NC}"
echo -e "${BLUE}║                                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  总测试套件数: ${BOLD}$TOTAL_SUITES${NC}"
echo -e "  ${GREEN}通过: $PASSED_SUITES${NC}"
echo -e "  ${RED}失败: $FAILED_SUITES${NC}"

if [ $TOTAL_SUITES -gt 0 ]; then
    pass_rate=$((PASSED_SUITES * 100 / TOTAL_SUITES))
    echo -e "  通过率: ${BOLD}${pass_rate}%${NC}"
fi

echo ""

if [ $FAILED_SUITES -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✅ 所有测试套件通过！${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}❌ 有 $FAILED_SUITES 个测试套件失败${NC}"
    echo ""
    exit 1
fi
