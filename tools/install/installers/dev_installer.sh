#!/bin/bash
# SAGE 安装脚本 - 开发工具包安装器
# 负责安装开发工具相关的依赖包

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../ui/colors.sh"

# 导入核心安装器函数
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"

# C++扩展安装已移至main_installer.sh中的标准安装流程

# 安装开发包

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

install_dev_packages() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🛠️  开发工具安装完成${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    log_info "开发工具安装阶段" "DevTools"

    echo -e "${CHECK} 开发工具依赖已在 in-tree sage-dev / isage[dev] 安装过程中完成"
    echo -e "${DIM}包含: black, isort, flake8, pytest, pytest-timeout, mypy, pre-commit 等${NC}"
    echo -e "${DIM}开发工具由主仓内置的 sage-dev 统一维护${NC}"
    echo ""

    # 验证关键开发工具是否可用
    echo -e "${BOLD}  🔍 验证开发工具可用性...${NC}"
    echo ""

    local tools_to_check=("black" "isort" "flake8" "pytest")
    local missing_tools=()

    for tool in "${tools_to_check[@]}"; do
        # 优先尝试直接调用（在 PATH 中）
        if command -v "$tool" >/dev/null 2>&1; then
            log_info "$tool 可用" "DevTools"
            echo -e "${CHECK} $tool 可用"
        # 降级方案：尝试通过 python -m 方式调用
        elif python3 -m "$tool" --version >/dev/null 2>&1 || python3 -m pip show "$tool" >/dev/null 2>&1; then
            log_info "$tool 可用（通过 python -m）" "DevTools"
            echo -e "${CHECK} $tool 可用（通过 python -m）"
        else
            log_warn "$tool 不可用" "DevTools"
            echo -e "${WARNING} $tool 不可用"
            missing_tools+=("$tool")
        fi
    done

    # 验证关键CLI包是否可导入（这些包对Examples测试很重要）
    echo ""
    echo -e "${BOLD}  🔍 验证CLI依赖包可用性...${NC}"
    echo ""

    local cli_packages_to_check=("typer" "rich")
    for package in "${cli_packages_to_check[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            log_info "$package 可导入" "DevTools"
            echo -e "${CHECK} $package 可导入"
        else
            log_warn "$package 无法导入" "DevTools"
            echo -e "${WARNING} $package 无法导入"
            missing_tools+=("$package")
        fi
    done

    if [ ${#missing_tools[@]} -eq 0 ]; then
        echo ""
        log_info "所有开发工具验证成功！" "DevTools"
        echo -e "${CHECK} 所有开发工具验证成功！"
    else
        echo ""
        log_warn "部分工具不可用: ${missing_tools[*]}" "DevTools"
        echo -e "${WARNING} 部分工具不可用: ${missing_tools[*]}"
        echo -e "${DIM}建议运行: pip install ${missing_tools[*]}${NC}"
    fi

    echo ""

    # C++扩展已在标准安装流程中安装完成
    echo -e "${BOLD}  ℹ️  C++扩展已在标准安装流程中完成${NC}"

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  🎉 开发工具安装完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    log_info "开发工具安装完成" "DevTools"
}
