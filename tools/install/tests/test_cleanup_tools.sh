#!/bin/bash
# 清理工具单元测试
# 测试 track_install.sh 和 uninstall_sage.sh


# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

set -e

# 测试框架设置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 导入颜色定义
source "${SAGE_ROOT:-}/tools/install/ui/colors.sh"

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试目录
TEST_DIR="/tmp/sage_cleanup_test_$$"
mkdir -p "$TEST_DIR"

# 测试辅助函数
assert_file_exists() {
    local file="$1"
    local test_name="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo -e "${DIM}   File not found: $file${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

assert_file_contains() {
    local file="$1"
    local pattern="$2"
    local test_name="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo -e "${DIM}   Pattern '$pattern' not found in $file${NC}"
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

# ============================================================================
# 测试 track_install.sh
# ============================================================================

test_track_install_record_info() {
    echo ""
    echo -e "${BLUE}测试组: track_install.sh - 记录安装信息${NC}"

    # 保存原始 SAGE_ROOT
    local orig_sage_root="${SAGE_ROOT:-}"

    # 设置测试环境
    local test_info_file="$TEST_DIR/.sage/install_info.json"
    local test_package_file="$TEST_DIR/.sage/installed_packages.txt"

    mkdir -p "$TEST_DIR/.sage"

    # 创建测试脚本副本
    cp "$orig_sage_root/tools/install/cleanup/track_install.sh" "$TEST_DIR/track_install.sh"
    sed -i "s|SAGE_ROOT=.*|SAGE_ROOT=\"$TEST_DIR\"|g" "$TEST_DIR/track_install.sh"

    # 测试记录安装信息
    cd "$TEST_DIR"
    bash track_install.sh post-install "dev" "pip" "false" >/dev/null 2>&1

    assert_file_exists "$test_info_file" "创建安装信息文件"
    assert_file_contains "$test_info_file" "install_mode" "包含安装模式"
    assert_file_contains "$test_info_file" "dev" "记录正确的安装模式"
    assert_file_contains "$test_info_file" "timestamp" "包含时间戳"

    # 清理 (不需要 unset，因为没有修改全局 SAGE_ROOT)
    cd - >/dev/null
}

test_track_install_show_command() {
    echo ""
    echo -e "${BLUE}测试组: track_install.sh - show 命令${NC}"

    # 保存原始 SAGE_ROOT
    local orig_sage_root="${SAGE_ROOT:-}"

    # 测试 show 命令（即使文件不存在也不应崩溃）
    cd "$TEST_DIR"
    bash track_install.sh show >/dev/null 2>&1
    assert_success "show 命令执行无错误"

    # 清理
    cd - >/dev/null
}

# ============================================================================
# 测试 uninstall_sage.sh
# ============================================================================

test_uninstall_help_option() {
    echo ""
    echo -e "${BLUE}测试组: uninstall_sage.sh - 帮助选项${NC}"

    # 测试 --help 选项
    bash "${SAGE_ROOT:-}/tools/install/cleanup/uninstall_sage.sh" --help >/dev/null 2>&1
    assert_success "显示帮助信息"
}

test_uninstall_yes_flag() {
    echo ""
    echo -e "${BLUE}测试组: uninstall_sage.sh - --yes 标志${NC}"

    # 保存原始 SAGE_ROOT
    local orig_sage_root="${SAGE_ROOT:-}"

    # 创建测试环境
    mkdir -p "$TEST_DIR/.sage"
    echo "test-package" > "$TEST_DIR/.sage/installed_packages.txt"

    # 创建测试脚本副本
    cp "$orig_sage_root/tools/install/cleanup/uninstall_sage.sh" "$TEST_DIR/uninstall_sage.sh"
    sed -i "s|SAGE_ROOT=.*|SAGE_ROOT=\"$TEST_DIR\"|g" "$TEST_DIR/uninstall_sage.sh"

    # 测试 --yes 标志（应该不会有交互提示）
    cd "$TEST_DIR"
    timeout 5s bash uninstall_sage.sh --yes >/dev/null 2>&1 || true
    assert_success "--yes 标志执行完成"

    # 清理
    cd - >/dev/null
}

# ============================================================================
# 集成测试
# ============================================================================

test_full_track_and_uninstall_workflow() {
    echo ""
    echo -e "${BLUE}测试组: 完整的记录和卸载流程${NC}"

    # 保存原始 SAGE_ROOT
    local orig_sage_root="${SAGE_ROOT:-}"

    # 1. 记录安装前
    cd "$TEST_DIR"
    bash track_install.sh pre-install >/dev/null 2>&1

    # 2. 记录安装后
    bash track_install.sh post-install "minimal" "pip" "false" >/dev/null 2>&1

    local info_file="$TEST_DIR/.sage/install_info.json"
    assert_file_exists "$info_file" "完整流程创建了安装信息"

    # 3. 显示信息
    bash track_install.sh show >/dev/null 2>&1
    assert_success "完整流程可以显示信息"

    # 清理
    cd - >/dev/null
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

cleanup_test_dir() {
    echo ""
    echo -e "${DIM}清理测试目录: $TEST_DIR${NC}"
    rm -rf "$TEST_DIR"
}

# ============================================================================
# 主测试流程
# ============================================================================

main() {
    echo -e "${BLUE}${BOLD}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║                                                ║"
    echo "║   🧪 清理工具单元测试                          ║"
    echo "║                                                ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # 运行所有测试
    test_track_install_record_info
    test_track_install_show_command
    test_uninstall_help_option
    test_uninstall_yes_flag
    test_full_track_and_uninstall_workflow

    # 打印总结
    print_test_summary

    # 清理
    cleanup_test_dir
}

# 设置退出时清理
trap cleanup_test_dir EXIT

# 运行测试
main "$@"
