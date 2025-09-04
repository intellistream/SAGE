#!/bin/bash
# SAGE 安装脚本 - 环境配置管理器
# 统一管理安装环境的配置和设置

# 导入相关模块
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../examination_tools/comprehensive_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/conda_manager.sh"



# 配置安装环境的主函数
configure_installation_environment() {
    local install_environment="${1:-conda}"
    local install_mode="${2:-dev}"
    local conda_env_name="${3:-}"  # 可选的conda环境名
    
    # 设置环境变量以避免用户站点包干扰虚拟环境
    export PYTHONNOUSERSITE=1
    echo -e "${INFO} 已设置 PYTHONNOUSERSITE=1 以避免用户包冲突"
    
    # 运行综合系统检查（包含预检查、系统检查、SAGE检查）
    if ! comprehensive_system_check "$install_mode" "$install_environment"; then
        echo -e "${CROSS} 系统环境检查失败，安装终止"
        exit 1
    fi
    
    # 根据参数配置环境
    case "$install_environment" in
        "conda")
            # conda 模式已在检查中验证过
            if [ -n "$conda_env_name" ]; then
                echo -e "${INFO} 将使用指定的conda环境: $conda_env_name"
                # 导出环境名供其他脚本使用
                export SAGE_ENV_NAME="$conda_env_name"
            fi
            ask_conda_environment
            ;;
        "pip")
            # pip 模式已在检查中验证过
            echo -e "${INFO} 使用系统 Python 环境安装"
            export PIP_CMD="python3 -m pip"
            export PYTHON_CMD="python3"
            ;;
        *)
            echo -e "${CROSS} 未知的安装环境: $install_environment"
            exit 1
            ;;
    esac
    
    # 设置默认命令（如果没有设置 conda 环境）
    export PIP_CMD="${PIP_CMD:-python3 -m pip}"
    export PYTHON_CMD="${PYTHON_CMD:-python3}"
    
    echo -e "${CHECK} 环境配置完成"
}
