#!/bin/bash
# 环境配置模块单元测试
# 测试 environment_config.sh 中的新增函数

set -e

# 测试框架设置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 导入被测试模块
source "$SAGE_ROOT/tools/install/display_tools/colors.sh"
source "$SAGE_ROOT/tools/install/download_tools/environment_config.sh"

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试辅助函数
assert_equals() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo -e "${DIM}   Expected: '$expected'${NC}"
        echo -e "${DIM}   Actual:   '$actual'${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local test_name="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [[ "$haystack" == *"$needle"* ]]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo -e "${DIM}   Expected to contain: '$needle'${NC}"
        echo -e "${DIM}   In: '$haystack'${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

assert_success() {
    local test_name="$1"
    local exit_code=$?

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name (exit code: $exit_code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

assert_failure() {
    local test_name="$1"
    local exit_code=$?

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ $exit_code -ne 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name (expected non-zero exit code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# ============================================================================
# 测试 detect_virtual_environment
# ============================================================================

test_detect_venv_in_conda() {
    echo ""
    echo -e "${BLUE}测试组: detect_virtual_environment - Conda 环境${NC}"

    # 模拟 Conda 环境
    export CONDA_DEFAULT_ENV="test-env"
    export CONDA_PREFIX="/path/to/conda/envs/test-env"
    unset VIRTUAL_ENV

    local result=$(detect_virtual_environment)
    local is_venv=$(echo "$result" | cut -d'|' -f1)
    local venv_type=$(echo "$result" | cut -d'|' -f2)
    local venv_name=$(echo "$result" | cut -d'|' -f3)

    assert_equals "true" "$is_venv" "检测到 Conda 环境"
    assert_equals "conda" "$venv_type" "环境类型为 conda"
    assert_equals "test-env" "$venv_name" "环境名称正确"

    # 清理
    unset CONDA_DEFAULT_ENV CONDA_PREFIX
}

test_detect_venv_in_python_venv() {
    echo ""
    echo -e "${BLUE}测试组: detect_virtual_environment - Python venv${NC}"

    # 模拟 Python venv
    export VIRTUAL_ENV="/path/to/venv"
    unset CONDA_DEFAULT_ENV CONDA_PREFIX

    local result=$(detect_virtual_environment)
    local is_venv=$(echo "$result" | cut -d'|' -f1)
    local venv_type=$(echo "$result" | cut -d'|' -f2)
    local venv_name=$(echo "$result" | cut -d'|' -f3)

    assert_equals "true" "$is_venv" "检测到 Python venv"
    assert_equals "venv" "$venv_type" "环境类型为 venv"
    assert_equals "venv" "$venv_name" "环境名称正确"

    # 清理
    unset VIRTUAL_ENV
}

test_detect_venv_in_system() {
    echo ""
    echo -e "${BLUE}测试组: detect_virtual_environment - 系统环境${NC}"

    # 清除所有虚拟环境标记
    unset CONDA_DEFAULT_ENV CONDA_PREFIX VIRTUAL_ENV

    local result=$(detect_virtual_environment)
    local is_venv=$(echo "$result" | cut -d'|' -f1)
    local venv_type=$(echo "$result" | cut -d'|' -f2)

    assert_equals "false" "$is_venv" "未检测到虚拟环境"
    assert_equals "" "$venv_type" "环境类型为空"
}

# ============================================================================
# 测试 ensure_python_venv
# ============================================================================

test_ensure_python_venv_creation() {
    echo ""
    echo -e "${BLUE}测试组: ensure_python_venv${NC}"

    # 创建临时测试目录
    local test_venv="/tmp/sage_test_venv_$$"

    # 清理可能存在的旧测试环境
    rm -rf "$test_venv"

    # 测试创建虚拟环境
    if ensure_python_venv "$test_venv" 2>/dev/null; then
        assert_success "创建虚拟环境成功"

        # 验证虚拟环境结构
        if [ -f "$test_venv/bin/activate" ]; then
            assert_success "虚拟环境包含 activate 脚本"
        else
            assert_failure "虚拟环境缺少 activate 脚本"
            false
        fi

        if [ -f "$test_venv/bin/python" ] || [ -f "$test_venv/bin/python3" ]; then
            assert_success "虚拟环境包含 Python 可执行文件"
        else
            assert_failure "虚拟环境缺少 Python 可执行文件"
            false
        fi
    else
        echo -e "${YELLOW}⚠️  SKIP${NC}: 创建虚拟环境 (可能缺少 python3-venv 或 virtualenv)"
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
    fi

    # 清理
    rm -rf "$test_venv"
}

# ============================================================================
# 测试 check_virtual_environment_isolation (非交互部分)
# ============================================================================

test_check_venv_skip_in_ci() {
    echo ""
    echo -e "${BLUE}测试组: check_virtual_environment_isolation - CI 跳过${NC}"

    # 模拟 CI 环境
    export CI="true"
    unset CONDA_DEFAULT_ENV CONDA_PREFIX VIRTUAL_ENV

    # 在 CI 中应该跳过检查
    check_virtual_environment_isolation "pip" "false" 2>/dev/null
    assert_success "CI 环境跳过虚拟环境检查"

    # 清理
    unset CI
}

test_check_venv_skip_for_conda_install() {
    echo ""
    echo -e "${BLUE}测试组: check_virtual_environment_isolation - Conda 安装跳过${NC}"

    unset CI CONDA_DEFAULT_ENV CONDA_PREFIX VIRTUAL_ENV

    # 选择 conda 安装模式时应该跳过检查
    check_virtual_environment_isolation "conda" "false" 2>/dev/null
    assert_success "Conda 安装模式跳过虚拟环境检查"
}

# ============================================================================
# 测试报告
# ============================================================================

print_test_summary() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}测试总结${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "总测试数: $TOTAL_TESTS"
    echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
    echo -e "${RED}失败: $FAILED_TESTS${NC}"

    local pass_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi
    echo -e "通过率: ${pass_rate}%"
    echo ""

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}${BOLD}✅ 所有测试通过！${NC}"
        return 0
    else
        echo -e "${RED}${BOLD}❌ 有测试失败${NC}"
        return 1
    fi
}

# ============================================================================
# 主测试流程
# ============================================================================

main() {
    echo -e "${BLUE}${BOLD}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║                                                ║"
    echo "║   🧪 环境配置模块单元测试                      ║"
    echo "║                                                ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # 运行所有测试
    test_detect_venv_in_conda
    test_detect_venv_in_python_venv
    test_detect_venv_in_system
    test_ensure_python_venv_creation
    test_check_venv_skip_in_ci
    test_check_venv_skip_for_conda_install

    # 打印总结
    print_test_summary
}

# 运行测试
main "$@"
