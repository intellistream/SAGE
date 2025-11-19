#!/bin/bash
# SAGE 安装脚本 - 开发工具包安装器
# 负责安装开发工具相关的依赖包

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 导入核心安装器函数
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"

# C++扩展安装已移至main_installer.sh中的标准安装流程

# 安装开发包
install_dev_packages() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🛠️  开发工具安装完成${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    log_info "开发工具安装阶段" "DevTools"

    echo -e "${CHECK} 开发工具依赖已在 sage-tools[dev] 安装过程中完成"
    echo -e "${DIM}包含: black, isort, flake8, pytest, pytest-timeout, mypy, pre-commit 等${NC}"
    echo -e "${DIM}所有依赖通过 packages/sage-tools/pyproject.toml 统一管理${NC}"
    echo ""

    # 验证关键开发工具是否可用
    echo -e "${BOLD}  🔍 验证开发工具可用性...${NC}"
    echo ""

    local tools_to_check=("black" "isort" "flake8" "pytest")
    local missing_tools=()

    for tool in "${tools_to_check[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            log_info "$tool 可用" "DevTools"
            echo -e "${CHECK} $tool 可用"
        else
            log_warn "$tool 不在 PATH 中" "DevTools"
            echo -e "${WARNING} $tool 不在 PATH 中"
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
        log_warn "部分工具不在 PATH 中: ${missing_tools[*]}" "DevTools"
        echo -e "${WARNING} 部分工具不在 PATH 中: ${missing_tools[*]}"
        echo -e "${DIM}这在某些环境中是正常的，工具仍可通过 python -m 方式使用${NC}"
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
