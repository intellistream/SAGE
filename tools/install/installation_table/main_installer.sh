#!/bin/bash
# SAGE 安装脚本 - 主安装控制器
# 统一管理不同安装模式的安装流程

# 导入所有安装器
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/interface.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../examination_tools/sage_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../download_tools/environment_config.sh"
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/scientific_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/dev_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/vllm_installer.sh"

# 主安装函数
install_sage() {
    local mode="${1:-dev}"
    local environment="${2:-conda}"
    local install_vllm="${3:-false}"
    
    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    
    echo ""
    echo -e "${GEAR} 开始安装 SAGE 包 (${mode} 模式, ${environment} 环境)..."
    if [ "$install_vllm" = "true" ]; then
        echo -e "${PURPLE}包含 VLLM 支持${NC}"
    fi
    echo ""
    
    # 配置安装环境（包含所有检查）
    configure_installation_environment "$environment" "$mode"
    
    # 记录安装开始到日志
    echo "" >> "$log_file"
    echo "========================================" >> "$log_file"
    echo "SAGE 主要安装过程开始 - $(date)" >> "$log_file"
    echo "安装模式: $mode" >> "$log_file"
    echo "安装环境: $environment" >> "$log_file"
    echo "安装 VLLM: $install_vllm" >> "$log_file"
    echo "PIP 命令: $PIP_CMD" >> "$log_file"
    echo "Python 命令: $PYTHON_CMD" >> "$log_file"
    echo "========================================" >> "$log_file"
    
    echo ""
    case "$mode" in
        "minimal")
            echo -e "${BLUE}最小安装模式：仅安装核心 SAGE 包${NC}"
            echo "$(date): 开始最小安装模式" >> "$log_file"
            install_core_packages "$mode"
            ;;
        "standard")
            echo -e "${BLUE}标准安装模式：核心包 + 科学计算库${NC}"
            echo -e "${DIM}包含: numpy, pandas, matplotlib, scipy, jupyter${NC}"
            echo "$(date): 开始标准安装模式" >> "$log_file"
            install_core_packages "$mode"
            install_scientific_packages
            ;;
        "dev")
            echo -e "${BLUE}开发者安装模式：标准包 + 开发工具${NC}"
            echo -e "${DIM}包含: 标准安装 + pytest, black, mypy, pre-commit${NC}"
            echo "$(date): 开始开发者安装模式" >> "$log_file"
            install_core_packages "$mode"
            install_scientific_packages
            install_dev_packages
            ;;
        *)
            echo -e "${WARNING} 未知安装模式: $mode，使用开发者模式"
            echo "$(date): 未知安装模式 $mode，使用开发者模式" >> "$log_file"
            install_core_packages "dev"
            install_scientific_packages
            install_dev_packages
            ;;
    esac
    
    echo ""
    echo -e "${CHECK} SAGE 安装完成！"
    
    # 安装 VLLM（如果需要）
    if [ "$install_vllm" = "true" ]; then
        echo ""
        install_vllm_packages
    fi
    
    # 记录安装完成
    echo "$(date): SAGE 安装完成" >> "$log_file"
    if [ "$install_vllm" = "true" ]; then
        echo "$(date): VLLM 安装请求已处理" >> "$log_file"
    fi
    echo "安装结束时间: $(date)" >> "$log_file"
    echo "========================================" >> "$log_file"
    
    # 显示安装信息
    show_install_success "$mode"
}
