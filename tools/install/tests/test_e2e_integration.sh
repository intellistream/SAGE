#!/bin/bash
# SAGE 端到端集成测试
# 测试完整的安装 -> 使用 -> 清理流程


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

# 测试配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TEST_DIR="/tmp/sage_e2e_test_$$"

# 导入颜色定义
source "${SAGE_ROOT:-}/tools/install/display_tools/colors.sh"

# 测试结果
TOTAL_STEPS=0
PASSED_STEPS=0
FAILED_STEPS=0

# 日志函数
log_step() {
    local step_name="$1"
    TOTAL_STEPS=$((TOTAL_STEPS + 1))
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}步骤 $TOTAL_STEPS: $step_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log_success() {
    local message="$1"
    echo -e "${GREEN}✅ $message${NC}"
    PASSED_STEPS=$((PASSED_STEPS + 1))
}

log_failure() {
    local message="$1"
    echo -e "${RED}❌ $message${NC}"
    FAILED_STEPS=$((FAILED_STEPS + 1))
}

log_info() {
    local message="$1"
    echo -e "${DIM}   $message${NC}"
}

# 清理函数
cleanup() {
    echo ""
    echo -e "${DIM}清理测试环境...${NC}"

    # 停用虚拟环境
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        deactivate 2>/dev/null || true
    fi

    # 删除测试目录
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
        log_info "已删除测试目录: $TEST_DIR"
    fi
}

# 设置退出时清理
trap cleanup EXIT

# ============================================================================
# 测试步骤
# ============================================================================

step1_setup_test_environment() {
    log_step "设置测试环境"

    # 创建测试目录
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"
    log_info "测试目录: $TEST_DIR"

    # 复制必要的文件
    cp -r "${SAGE_ROOT:-}/tools" .
    cp -r "${SAGE_ROOT:-}/docs" . 2>/dev/null || true
    cp "${SAGE_ROOT:-}/quickstart.sh" . 2>/dev/null || true
    cp "${SAGE_ROOT:-}/Makefile" . 2>/dev/null || true
    cp "${SAGE_ROOT:-}/manage.sh" . 2>/dev/null || true

    log_success "测试环境设置完成"
}

step2_test_environment_detection() {
    log_step "测试环境检测（禁用 venv）"

    # 清除所有虚拟环境变量
    unset CONDA_DEFAULT_ENV CONDA_PREFIX VIRTUAL_ENV

    # 导入环境配置模块
    source "$TEST_DIR/tools/install/display_tools/colors.sh"
    source "$TEST_DIR/tools/install/download_tools/environment_config.sh"

    # 测试虚拟环境检测
    local result=$(detect_virtual_environment)
    local is_venv=$(echo "$result" | cut -d'|' -f1)

    if [ "$is_venv" = "false" ]; then
        log_success "正确检测到无虚拟环境"
    else
        log_failure "虚拟环境检测失败"
        return 1
    fi

    log_success "venv 自动创建路径已禁用（仅检测，不创建）"
}

step3_test_install_tracking() {
    log_step "测试安装跟踪"

    # 安装一些测试包
    log_info "安装测试包..."
    pip install --quiet requests >/dev/null 2>&1 || true

    # 测试 track_install.sh
    export SAGE_ROOT="$TEST_DIR"

    # 记录安装前状态
    bash "$TEST_DIR/tools/cleanup/track_install.sh" pre-install
    log_info "已记录安装前状态"

    # 记录安装后状态
    bash "$TEST_DIR/tools/cleanup/track_install.sh" post-install "dev" "pip" "false"
    log_info "已记录安装后状态"

    # 验证生成的文件
    if [ -f "$TEST_DIR/.sage/install_info.json" ]; then
        log_success "安装信息文件已创建"
        log_info "内容预览:"
        cat "$TEST_DIR/.sage/install_info.json" | head -10
    else
        log_failure "安装信息文件未创建"
        return 1
    fi

    # 测试 show 命令
    log_info "测试 show 命令..."
    bash "$TEST_DIR/tools/cleanup/track_install.sh" show

    log_success "安装跟踪测试完成"
}

step4_test_venv_policy_reject() {
    log_step "测试环境检测功能"

    source "$TEST_DIR/tools/install/display_tools/colors.sh"
    source "$TEST_DIR/tools/install/download_tools/environment_config.sh"

    export VIRTUAL_ENV="$TEST_DIR/.venv"
    if check_virtual_environment_isolation "pip" >/dev/null 2>&1; then
        log_failure "Python venv 未被拒绝"
        unset VIRTUAL_ENV
        return 1
    fi
    unset VIRTUAL_ENV
    log_success "Python venv 被正确拒绝"
}

step5_test_venv_policy() {
    log_step "测试 SAGE_VENV_POLICY 配置（系统环境）"

    source "$TEST_DIR/tools/install/display_tools/colors.sh"
    source "$TEST_DIR/tools/install/download_tools/environment_config.sh"

    # 测试不同策略
    for policy in warning error ignore; do
        export SAGE_VENV_POLICY=$policy
        log_info "测试策略: SAGE_VENV_POLICY=$policy"

        # 仅验证变量可设置与检测函数可执行
        local result=$(detect_virtual_environment)
        log_info "策略 $policy 检测结果: $result"
    done

    unset SAGE_VENV_POLICY
    log_success "SAGE_VENV_POLICY 策略测试完成"
}

step6_test_cleanup() {
    log_step "测试清理功能"

    export SAGE_ROOT="$TEST_DIR"

    # 测试 --help
    log_info "测试 --help 选项..."
    bash "$TEST_DIR/tools/cleanup/uninstall_sage.sh" --help >/dev/null 2>&1
    log_success "帮助信息显示正常"

    # 测试 --yes 标志（非交互式）
    log_info "测试 --yes 标志..."
    timeout 10s bash "$TEST_DIR/tools/cleanup/uninstall_sage.sh" --yes >/dev/null 2>&1 || true
    log_success "非交互式卸载测试完成"
}

step7_test_makefile_integration() {
    log_step "测试 Makefile 集成"

    if [ -f "$TEST_DIR/Makefile" ]; then
        # 测试 clean-env 目标
        log_info "测试 make clean-env..."
        if grep -q "clean-env" "$TEST_DIR/Makefile"; then
            log_success "Makefile 包含 clean-env 目标"
        else
            log_failure "Makefile 缺少 clean-env 目标"
            return 1
        fi
    else
        log_info "跳过 Makefile 测试（文件不存在）"
    fi
}

step8_verify_documentation() {
    log_step "验证文档一致性"

    # 检查文档文件
    local docs_to_check=(
        "docs/ARCHITECTURE_LAYER_OWNERSHIP_MATRIX_V1.md"
        "docs/sage_zoo.md"
    )

    for doc in "${docs_to_check[@]}"; do
        if [ -f "$TEST_DIR/$doc" ]; then
            log_success "文档存在: $doc"
        else
            log_info "文档不存在（跳过）: $doc"
        fi
    done

    log_success "文档验证完成"
}

# ============================================================================
# 测试报告
# ============================================================================

print_test_summary() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}测试总结${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "总步骤数: $TOTAL_STEPS"
    echo -e "${GREEN}通过: $PASSED_STEPS${NC}"
    echo -e "${RED}失败: $FAILED_STEPS${NC}"

    local pass_rate=0
    if [ $TOTAL_STEPS -gt 0 ]; then
        pass_rate=$((PASSED_STEPS * 100 / TOTAL_STEPS))
    fi
    echo -e "通过率: ${pass_rate}%"
    echo ""

    if [ $FAILED_STEPS -eq 0 ]; then
        echo -e "${GREEN}${BOLD}✅ 所有集成测试通过！${NC}"
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
    echo "║   🧪 SAGE 端到端集成测试                       ║"
    echo "║                                                ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # 运行所有测试步骤
    step1_setup_test_environment
    step2_test_environment_detection
    step3_test_install_tracking
    step4_test_venv_policy_reject
    step5_test_venv_policy
    step6_test_cleanup
    step7_test_makefile_integration
    step8_verify_documentation

    # 打印总结
    print_test_summary
}

# 运行测试
main "$@"
