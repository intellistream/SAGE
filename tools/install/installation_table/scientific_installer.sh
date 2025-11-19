#!/bin/bash
# SAGE 安装脚本 - 科学计算包安装器
# 负责安装科学计算相关的依赖包

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 导入核心安装器函数
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"

# 安装科学计算包
install_scientific_packages() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  🔬 正在安装科学计算库...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    log_info "开始安装科学计算库" "Scientific"

    local packages=(
        "numpy>=2.0.0,<3.0.0"  # 与SAGE包保持一致的numpy版本
        "pandas>=1.3.0"
        "matplotlib>=3.4.0"
        "scipy>=1.15.0,<2.0.0"  # 与SAGE包保持一致的scipy版本
        "jupyter>=1.0.0"
        "ipykernel>=6.0.0"
    )

    for package in "${packages[@]}"; do
        echo -e "${BOLD}  📊 正在安装 $package${NC}"
        echo -e "${DIM}运行命令: $PIP_CMD install \"$package\"${NC}"
        echo ""

        if log_command "Scientific" "Install" "$PIP_CMD install \"$package\""; then
            log_info "$package 安装成功！" "Scientific"
            echo ""
            echo -e "${CHECK} $package 安装成功！"
            echo ""
        else
            log_warn "$package 安装可能失败，继续安装其他包..." "Scientific"
            echo ""
            echo -e "${WARNING} $package 安装可能失败，继续安装其他包..."
            echo ""
        fi
    done

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  🎉 科学计算库安装完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    log_info "科学计算库安装完成" "Scientific"
}
