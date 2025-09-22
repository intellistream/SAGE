#!/bin/bash

# SAGE Issues Manager 快速测试脚本
# 用于CI/CD或快速验证核心功能

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 测试计数器
TESTS_RUN=0
TESTS_PASSED=0

# 快速测试函数
quick_test() {
    local test_name="$1"
    local test_command="$2"
    
    ((TESTS_RUN++))
    echo -n "🧪 $test_name ... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌${NC}"
    fi
}

echo -e "${CYAN}⚡ SAGE Issues Manager 快速测试${NC}"
echo "=============================="
echo ""

cd "$SCRIPT_DIR"

# 核心脚本存在性检查
echo -e "${BLUE}📁 检查核心文件...${NC}"
quick_test "主脚本存在" "test -f issues_manager.sh"
quick_test "主脚本可执行" "test -x issues_manager.sh"
quick_test "主脚本语法正确" "bash -n issues_manager.sh"

# Python脚本检查
echo -e "${BLUE}🐍 检查Python脚本...${NC}"
python_scripts=(
    "_scripts/helpers/get_paths.py"
    "_scripts/copilot_issue_formatter.py"
    "_scripts/project_based_assign.py"
    "_scripts/issues_manager.py"
)

for script in "${python_scripts[@]}"; do
    if [ -f "$script" ]; then
        quick_test "$(basename "$script")" "python3 -m py_compile '$script'"
    fi
done

# 基础功能测试
echo -e "${BLUE}⚙️ 检查基础功能...${NC}"
quick_test "路径配置功能" "python3 _scripts/helpers/get_paths.py workspace"
quick_test "帮助信息显示" "python3 _scripts/issues_manager.py --help"

# 依赖检查
echo -e "${BLUE}📦 检查依赖...${NC}"
quick_test "Python3可用" "python3 --version"
quick_test "必要Python模块" "python3 -c 'import json, os, sys, datetime, pathlib'"

echo ""
echo -e "${CYAN}📊 测试结果${NC}"
echo "============"
echo -e "运行测试: ${BLUE}$TESTS_RUN${NC}"
echo -e "通过测试: ${GREEN}$TESTS_PASSED${NC}"
echo -e "成功率: ${CYAN}$(( TESTS_PASSED * 100 / TESTS_RUN ))%${NC}"

if [ $TESTS_PASSED -eq $TESTS_RUN ]; then
    echo -e "${GREEN}🎉 所有快速测试通过！${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️ 有 $(( TESTS_RUN - TESTS_PASSED )) 个测试失败${NC}"
    echo "💡 运行完整测试: ./test_issues_manager.sh"
    exit 1
fi
