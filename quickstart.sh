#!/bin/bash
# 🚀 SAGE 快速安装脚本 - 重构版本
# 模块化设计，分离关注点，便于维护

# 强制告诉 VS Code/xterm.js 支持 ANSI 和 256 色
export TERM=xterm-256color
set -e

# CI环境检测 - 设置非交互模式
if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
    export DEBIAN_FRONTEND=noninteractive
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    export PYTHONNOUSERSITE=1
    echo "🤖 CI环境检测到，启用非交互模式"
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$SCRIPT_DIR/tools/install"

# 导入所有模块
source "$TOOLS_DIR/display_tools/colors.sh"
source "$TOOLS_DIR/display_tools/output_formatter.sh"
source "$TOOLS_DIR/display_tools/interface.sh"
source "$TOOLS_DIR/examination_tools/system_check.sh"
source "$TOOLS_DIR/examination_tools/comprehensive_check.sh"
source "$TOOLS_DIR/download_tools/argument_parser.sh"
source "$TOOLS_DIR/installation_table/main_installer.sh"

# 在脚本开始时立即进行偏移探测
pre_check_system_environment

# 根据偏移探测结果设置Unicode符号
setup_unicode_symbols

# 主函数
main() {
    # 解析命令行参数（包括帮助检查）
    parse_arguments "$@"
    
    # 获取解析后的参数
    local mode=$(get_install_mode)
    local environment=$(get_install_environment)
    local conda_env_name=$(get_conda_env_name)
    
    # 显示欢迎界面
    show_welcome
    
    # 切换到项目根目录
    cd "$SCRIPT_DIR"
    
    # 执行安装
    install_sage "$mode" "$environment" "$conda_env_name"
    
    # 验证安装
    if verify_installation; then
        show_usage_tips "$mode"
        echo ""
        center_text "${ROCKET} 欢迎使用 SAGE！${ROCKET}" "$GREEN$BOLD"
        echo ""
    else
        echo ""
        echo -e "${YELLOW}安装可能成功，请手动验证：${NC}"
        echo -e "  python3 -c \"import sage; print(sage.__version__)\""
    fi
}

# 运行主函数
main "$@"
