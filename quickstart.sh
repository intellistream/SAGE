#!/bin/bash
# 🚀 SAGE 快速安装脚本 - 重构版本
# 模块化设计，分离关注点，便于维护

# 强制告诉 VS Code/xterm.js 支持 ANSI 和 256 色
export TERM=xterm-256color
set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$SCRIPT_DIR/installer"

# 导入所有模块
source "$TOOLS_DIR/display_tools/colors.sh"
source "$TOOLS_DIR/display_tools/output_formatter.sh"
source "$TOOLS_DIR/display_tools/interface.sh"
source "$TOOLS_DIR/examination_tools/system_check.sh"
source "$TOOLS_DIR/examination_tools/comprehensive_check.sh"
source "$TOOLS_DIR/download_tools/argument_parser.sh"
source "$TOOLS_DIR/installation_table/main_installer.sh"
source "$TOOLS_DIR/fixes/environment_doctor.sh"
source "$TOOLS_DIR/fixes/numpy_fix.sh"
source "$TOOLS_DIR/fixes/friendly_error_handler.sh"

# 在脚本开始时立即进行偏移探测
pre_check_system_environment

# 根据偏移探测结果设置Unicode符号
setup_unicode_symbols

# 主函数
main() {
    # 解析命令行参数（包括帮助检查）
    parse_arguments "$@"
    
    # 检查环境医生模式
    local run_doctor=$(get_run_doctor)
    local doctor_only=$(get_doctor_only)
    local fix_environment=$(get_fix_environment)
    
    if [ "$run_doctor" = "true" ]; then
        # 导入环境医生功能
        if [ -f "$TOOLS_DIR/fixes/environment_doctor.sh" ]; then
            source "$TOOLS_DIR/fixes/environment_doctor.sh"
            
            if [ "$fix_environment" = "true" ]; then
                run_full_diagnosis
                run_auto_fixes
            else
                run_full_diagnosis
            fi
            
            if [ "$doctor_only" = "true" ]; then
                exit $?
            fi
        else
            echo -e "${RED}错误：环境医生模块未找到${NC}"
            exit 1
        fi
    fi
    
    # 设置智能默认值并显示提示
    set_defaults_and_show_tips
    
    # 显示欢迎界面
    show_welcome
    
    # 环境预检查（除非在医生模式中）
    if [ "$run_doctor" != "true" ]; then
        echo -e "\n${BLUE}🔍 安装前环境检查${NC}"
        
        # 确保.sage目录存在
        mkdir -p .sage/logs
        
        if ! precheck_numpy_environment ".sage/logs/install.log"; then
            echo -e "${YELLOW}⚠️  检测到潜在环境问题，但将继续尝试安装${NC}"
        fi
    fi
    
    # 如果没有指定任何参数且不在 CI 环境中，显示交互式菜单
    if [ $# -eq 0 ] && [[ -z "$CI" && -z "$GITHUB_ACTIONS" && -z "$GITLAB_CI" && -z "$JENKINS_URL" && -z "$BUILDKITE" ]]; then
        show_installation_menu
    fi
    
    # 获取解析后的参数
    local mode=$(get_install_mode)
    local environment=$(get_install_environment)
    local install_vllm=$(get_install_vllm)
    local auto_confirm=$(get_auto_confirm)
    local clean_cache=$(get_clean_pip_cache)
    
    # 如果不是自动确认模式，显示最终确认
    if [ "$auto_confirm" != "true" ]; then
        echo ""
        echo -e "${BLUE}📋 最终安装配置：${NC}"
        show_install_configuration
        
        echo -e "${YELLOW}确认开始安装吗？${NC} [${GREEN}Y${NC}/${RED}n${NC}]"
        read -p "请输入选择: " -r continue_choice
        
        if [[ ! "$continue_choice" =~ ^[Yy]$ ]] && [[ ! -z "$continue_choice" ]]; then
            echo ""
            echo -e "${INFO} 安装已取消。"
            echo -e "${DIM}提示: 可使用 ./quickstart.sh --help 查看所有选项${NC}"
            echo -e "${DIM}提示: 使用 --yes 参数可跳过此确认步骤${NC}"
            exit 0
        fi
    else
        echo ""
        echo -e "${INFO} 使用自动确认模式，直接开始安装..."
        show_install_configuration
    fi
    
    # 切换到项目根目录
    cd "$SCRIPT_DIR"
    
    # 执行安装
    install_sage "$mode" "$environment" "$install_vllm" "$clean_cache"
    
    # 验证安装
    if verify_installation; then
        show_usage_tips "$mode"
        # 如果安装了 VLLM，验证 VLLM 安装
        if [ "$install_vllm" = "true" ]; then
            echo ""
            verify_vllm_installation
        fi
        echo ""
        # 使用适配的居中显示函数，确保在所有环境下都能正确居中
        if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
            center_text_formatted "${ROCKET} 欢迎使用 SAGE！${ROCKET}" "$GREEN$BOLD"
        else
            center_text "${ROCKET} 欢迎使用 SAGE！${ROCKET}" "$GREEN$BOLD"
        fi
        echo ""
    else
        echo ""
        echo -e "${YELLOW}安装可能成功，请手动验证：${NC}"
        echo -e "  python3 -c \"import sage; print(sage.__version__)\""
        if [ "$install_vllm" = "true" ]; then
            echo -e "  python3 -c \"import vllm; print(vllm.__version__)\""
        fi
    fi
}

# 运行主函数
main "$@"
