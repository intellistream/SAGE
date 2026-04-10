#!/bin/bash
# SAGE 安装验证工具
# 验证本地安装是否与 CI/CD 保持一致
#
# 用法:
#   ./tools/install/validate_installation.sh [选项]
#
# 选项:
#   --fix           自动修复检测到的问题
#   --strict        严格模式，任何警告都返回失败
#   --ci-compare    与 CI/CD 配置进行详细对比
#   --help          显示此帮助信息


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

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
DIM='\033[2m'
BOLD='\033[1m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 默认选项
FIX_ISSUES=false
STRICT_MODE=false
CI_COMPARE=false

# 统计
CHECKS_PASSED=0
CHECKS_WARNED=0
CHECKS_FAILED=0

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fix)
                FIX_ISSUES=true
                shift
                ;;
            --strict)
                STRICT_MODE=true
                shift
                ;;
            --ci-compare)
                CI_COMPARE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}未知选项: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
}

# 显示帮助信息
show_help() {
    cat << EOF
${BOLD}SAGE 安装验证工具${NC}

验证本地安装是否与 CI/CD 保持一致，避免 "CI通过但本地失败" 的问题。

${BOLD}用法:${NC}
  $0 [选项]

${BOLD}选项:${NC}
  --fix           自动修复检测到的问题
  --strict        严格模式，任何警告都返回失败
  --ci-compare    与 CI/CD 配置进行详细对比
  --help          显示此帮助信息

${BOLD}示例:${NC}
  $0                    # 运行基本验证
  $0 --fix              # 运行验证并自动修复问题
  $0 --strict           # 严格模式验证
  $0 --ci-compare       # 详细对比 CI/CD 配置

EOF
}

# 打印标题
print_header() {
    echo ""
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║         SAGE 安装验证工具 v1.0                           ║${NC}"
    echo -e "${BOLD}${CYAN}║         确保本地安装与 CI/CD 环境一致                    ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 记录检查结果
log_check() {
    local status="$1"
    local message="$2"
    local details="${3:-}"

    case "$status" in
        "pass")
            echo -e "  ${GREEN}✓${NC} $message"
            ((CHECKS_PASSED++))
            ;;
        "warn")
            echo -e "  ${YELLOW}⚠${NC} $message"
            [ -n "$details" ] && echo -e "    ${DIM}$details${NC}"
            ((CHECKS_WARNED++))
            ;;
        "fail")
            echo -e "  ${RED}✗${NC} $message"
            [ -n "$details" ] && echo -e "    ${DIM}$details${NC}"
            ((CHECKS_FAILED++))
            ;;
        "info")
            echo -e "  ${BLUE}ℹ${NC} $message"
            [ -n "$details" ] && echo -e "    ${DIM}$details${NC}"
            ;;
    esac
}

# 1. 验证安装方法
validate_installation_method() {
    echo -e "${BOLD}${BLUE}[1/7] 验证安装方法${NC}"
    echo ""

    # 检查 .sage 目录
    if [ -d "$SAGE_ROOT/.sage" ]; then
        log_check "pass" "发现 .sage 目录（quickstart.sh 创建）"

        # 检查安装日志
        if [ -f "$SAGE_ROOT/.sage/logs/install.log" ]; then
            log_check "pass" "安装日志存在"

            # 分析日志内容
            if grep -q "quickstart" "$SAGE_ROOT/.sage/logs/install.log" 2>/dev/null; then
                log_check "pass" "确认使用 quickstart.sh 安装" "这与 CI/CD 的安装方式一致"
            else
                log_check "warn" "安装日志中未找到 quickstart 标记" "可能使用了其他安装方式"
            fi
        else
            log_check "warn" "未找到安装日志" "建议重新使用 quickstart.sh 安装"
        fi
    else
        log_check "fail" "未找到 .sage 目录" "请使用 quickstart.sh 安装"

        if [ "$FIX_ISSUES" = true ]; then
            echo ""
            echo -e "    ${YELLOW}🔧 修复：准备运行 quickstart.sh...${NC}"
            read -p "    确认运行 './quickstart.sh --dev --yes' ? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cd "$SAGE_ROOT"
                ./quickstart.sh --dev --yes
            fi
        fi
    fi

    echo ""
}

# 2. 验证包安装方式
validate_package_installation() {
    echo -e "${BOLD}${BLUE}[2/7] 验证包安装方式${NC}"
    echo ""

    if command -v pip >/dev/null 2>&1 || command -v pip3 >/dev/null 2>&1; then
        local pip_cmd="pip"
        command -v pip3 >/dev/null 2>&1 && pip_cmd="pip3"

        # 检查 SAGE 包
        local sage_packages=$($pip_cmd list --format=freeze 2>/dev/null | grep -E "^isage|^-e.*sage" || true)

        if [ -n "$sage_packages" ]; then
            # 检查是否是可编辑安装
            local editable_count=$(echo "$sage_packages" | grep -c "^-e" || echo "0")
            local total_count=$(echo "$sage_packages" | wc -l)

            if [ "$editable_count" -eq "$total_count" ]; then
                log_check "pass" "所有 SAGE 包都是可编辑安装" "开发模式，与 'quickstart.sh --dev' 一致"
            elif [ "$editable_count" -gt 0 ]; then
                log_check "warn" "混合安装模式检测到" "$editable_count/$total_count 是可编辑安装"
                log_check "info" "建议：卸载并使用 quickstart.sh 重新安装"
            else
                log_check "warn" "非可编辑安装" "可能手动使用了 'pip install isage'"
                log_check "info" "CI/CD 使用可编辑安装，建议本地也使用相同方式"
            fi

            # 显示已安装的包
            echo -e "    ${DIM}已安装的 SAGE 包：${NC}"
            echo "$sage_packages" | sed 's/^/      /'
        else
            log_check "warn" "未检测到已安装的 SAGE 包" "请使用 quickstart.sh 安装"
        fi
    else
        log_check "fail" "pip 命令不可用"
    fi

    echo ""
}

# 3. 验证 Python 环境
validate_python_environment() {
    echo -e "${BOLD}${BLUE}[3/7] 验证 Python 环境${NC}"
    echo ""

    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1 | awk '{print $2}')
        local python_major=$(echo "$python_version" | cut -d. -f1)
        local python_minor=$(echo "$python_version" | cut -d. -f2)

        log_check "info" "Python 版本: $python_version"

        # CI/CD 使用 Python 3.11, 3.12
        if [ "$python_major" -eq 3 ] && [ "$python_minor" -ge 11 ] && [ "$python_minor" -le 12 ]; then
            log_check "pass" "Python 版本兼容" "CI/CD 支持 Python 3.11-3.12"
        elif [ "$python_major" -eq 3 ] && [ "$python_minor" -ge 11 ]; then
            log_check "warn" "Python 版本可用但未在 CI 中测试" "CI/CD 主要测试 3.11-3.12"
        else
            log_check "fail" "Python 版本不兼容" "需要 Python 3.11 或更高版本"
        fi

        # 检查虚拟环境
        if [ -n "$VIRTUAL_ENV" ] || [ -n "$CONDA_DEFAULT_ENV" ]; then
            local env_name="${CONDA_DEFAULT_ENV:-$(basename $VIRTUAL_ENV)}"
            log_check "pass" "在虚拟环境中: $env_name" "推荐做法"
        else
            log_check "warn" "未在虚拟环境中" "建议使用虚拟环境或 conda"
        fi
    else
        log_check "fail" "python3 命令不可用"
    fi

    echo ""
}

# 4. 验证系统依赖
validate_system_dependencies() {
    echo -e "${BOLD}${BLUE}[4/7] 验证系统依赖${NC}"
    echo ""

    # 检查 C++ 编译工具
    if command -v gcc >/dev/null 2>&1 && command -v g++ >/dev/null 2>&1; then
        local gcc_version=$(gcc --version | head -n1)
        log_check "pass" "C++ 编译器已安装: $gcc_version"
    else
        log_check "fail" "C++ 编译器未安装" "C++ 扩展无法构建"

        if [ "$FIX_ISSUES" = true ]; then
            echo -e "    ${YELLOW}🔧 修复建议：${NC}"
            echo -e "    ${DIM}sudo apt-get install build-essential${NC}"
        fi
    fi

    # 检查 CMake
    if command -v cmake >/dev/null 2>&1; then
        local cmake_version=$(cmake --version | head -n1 | awk '{print $3}')
        log_check "pass" "CMake 已安装: $cmake_version"
    else
        log_check "warn" "CMake 未安装" "某些 C++ 扩展可能无法构建"

        if [ "$FIX_ISSUES" = true ]; then
            echo -e "    ${YELLOW}🔧 修复建议：${NC}"
            echo -e "    ${DIM}sudo apt-get install cmake${NC}"
        fi
    fi

    # 检查 Git
    if command -v git >/dev/null 2>&1; then
        local git_version=$(git --version | awk '{print $3}')
        log_check "pass" "Git 已安装: $git_version"
    else
        log_check "fail" "Git 未安装" "子模块管理需要 Git"
    fi

    echo ""
}

# 5. 验证 Git 子模块
validate_git_submodules() {
    echo -e "${BOLD}${BLUE}[5/7] 验证 Git 子模块${NC}"
    echo ""

    if [ -d "$SAGE_ROOT/.git" ] && [ -f "$SAGE_ROOT/.gitmodules" ]; then
        log_check "pass" "Git 仓库包含子模块"

        # 检查未初始化的子模块
        local uninit_count=$(git -C "$SAGE_ROOT" submodule status 2>/dev/null | grep -c "^-" || echo "0")
        local total_count=$(git -C "$SAGE_ROOT" submodule status 2>/dev/null | wc -l || echo "0")

        if [ "$uninit_count" -eq 0 ] && [ "$total_count" -gt 0 ]; then
            log_check "pass" "所有 $total_count 个子模块已初始化"
        elif [ "$uninit_count" -gt 0 ]; then
            log_check "warn" "$uninit_count/$total_count 个子模块未初始化"

            if [ "$FIX_ISSUES" = true ]; then
                echo -e "    ${YELLOW}🔧 修复：初始化子模块...${NC}"
                git -C "$SAGE_ROOT" submodule update --init --recursive
                log_check "pass" "子模块已初始化"
            else
                log_check "info" "运行: git submodule update --init --recursive"
            fi
        fi
    else
        log_check "info" "不在 Git 仓库中或无子模块"
    fi

    echo ""
}

# 6. 验证 Git Hooks
validate_git_hooks() {
    echo -e "${BOLD}${BLUE}[6/7] 验证 Git Hooks${NC}"
    echo ""

    if [ -d "$SAGE_ROOT/.git/hooks" ]; then
        # 检查 pre-commit hook
        if [ -f "$SAGE_ROOT/.git/hooks/pre-commit" ]; then
            log_check "pass" "pre-commit hook 已安装"

            # 检查是否使用 pre-commit 框架
            if grep -q "pre-commit" "$SAGE_ROOT/.git/hooks/pre-commit" 2>/dev/null; then
                log_check "pass" "使用 pre-commit 框架"
            fi
        else
            log_check "warn" "pre-commit hook 未安装" "代码质量检查将被跳过"

            if [ "$FIX_ISSUES" = true ] && command -v sage-dev >/dev/null 2>&1; then
                echo -e "    ${YELLOW}🔧 修复：安装 Git hooks...${NC}"
                sage-dev maintain hooks install
            else
                log_check "info" "运行: sage-dev maintain hooks install"
            fi
        fi

        # 检查 pre-commit 配置
        if [ -f "$SAGE_ROOT/.pre-commit-config.yaml" ]; then
            log_check "pass" "pre-commit 配置文件存在"
        fi
    else
        log_check "info" "不在 Git 仓库中"
    fi

    echo ""
}

# 7. CI/CD 配置对比
compare_with_ci_config() {
    echo -e "${BOLD}${BLUE}[7/7] CI/CD 配置对比${NC}"
    echo ""

    if [ "${CI:-}_COMPARE" = true ]; then
        # 提取 CI/CD 中使用的安装命令
        local ci_workflow="$SAGE_ROOT/.github/workflows/build-test.yml"

        if [ -f "$ci_workflow" ]; then
            log_check "info" "分析 CI/CD 配置..."

            # 检查 CI 是否使用 ci_install_wrapper.sh
            if grep -q "ci_install_wrapper.sh" "$ci_workflow"; then
                log_check "pass" "CI/CD 使用 ci_install_wrapper.sh" "确保与本地一致"
            else
                log_check "warn" "CI/CD 可能使用不同的安装方式"
            fi

            # 检查 CI Python 版本
            local ci_python=$(grep -A 2 "uses: actions/setup-python@" "$ci_workflow" | grep "python-version:" | head -1 | awk '{print $2}' | tr -d "'\"")
            if [ -n "$ci_python" ]; then
                log_check "info" "CI/CD Python 版本: $ci_python"
            fi

            # 检查 CI 使用的安装模式
            if grep -q "\-\-dev" "$ci_workflow"; then
                log_check "info" "CI/CD 使用开发模式 (--dev)" "本地也应使用相同模式"
            fi
        else
            log_check "warn" "未找到 CI/CD 配置文件"
        fi
    else
        log_check "info" "跳过详细 CI/CD 对比" "使用 --ci-compare 启用"
    fi

    echo ""
}

# 打印总结
print_summary() {
    echo ""
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}验证总结${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    echo -e "  ${GREEN}通过: $CHECKS_PASSED${NC}"
    echo -e "  ${YELLOW}警告: $CHECKS_WARNED${NC}"
    echo -e "  ${RED}失败: $CHECKS_FAILED${NC}"
    echo ""

    if [ $CHECKS_FAILED -eq 0 ] && [ $CHECKS_WARNED -eq 0 ]; then
        echo -e "${GREEN}${BOLD}✅ 所有检查通过！您的环境与 CI/CD 保持一致。${NC}"
    elif [ $CHECKS_FAILED -eq 0 ]; then
        echo -e "${YELLOW}${BOLD}⚠️  发现 $CHECKS_WARNED 个警告，但可以继续使用。${NC}"
        echo ""
        echo -e "${DIM}建议：使用 --fix 选项自动修复问题${NC}"
    else
        echo -e "${RED}${BOLD}❌ 发现 $CHECKS_FAILED 个严重问题，需要修复。${NC}"
        echo ""
        echo -e "${DIM}建议：${NC}"
        echo -e "${DIM}  1. 运行: ./quickstart.sh --dev --yes${NC}"
        echo -e "${DIM}  2. 或使用: $0 --fix${NC}"
    fi

    echo ""
    echo -e "${BOLD}保持环境一致的最佳实践：${NC}"
    echo -e "  • 始终使用 ${GREEN}quickstart.sh${NC} 安装"
    echo -e "  • 不要手动运行 ${YELLOW}pip install isage${NC}"
    echo -e "  • 定期运行此验证脚本"
    echo -e "  • 安装 Git hooks 确保代码质量"
    echo ""
}

# 主函数
main() {
    parse_args "$@"

    print_header

    # 运行所有验证
    validate_installation_method
    validate_package_installation
    validate_python_environment
    validate_system_dependencies
    validate_git_submodules
    validate_git_hooks
    compare_with_ci_config

    # 打印总结
    print_summary

    # 返回状态
    if [ $CHECKS_FAILED -gt 0 ]; then
        exit 1
    elif [ "$STRICT_MODE" = true ] && [ $CHECKS_WARNED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# 运行主函数
main "$@"
