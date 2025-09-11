#!/bin/bash
# SAGE 安装脚本 - 参数解析模块
# 处理命令行参数的解析和验证

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 全局变量
INSTALL_MODE=""
INSTALL_ENVIRONMENT=""
INSTALL_VLLM=false
SHOW_HELP=false

# 显示参数帮助信息
show_parameter_help() {
    echo ""
    echo -e "${BOLD}SAGE 快速安装脚本${NC}"
    echo ""
    echo -e "${BLUE}用法：${NC}"
    echo -e "  ./quickstart.sh [安装模式] [安装环境] [AI模型支持]"
    echo ""
    
    echo -e "${BLUE}📦 安装模式 (默认: 开发者模式)：${NC}"
    echo ""
    echo -e "  ${BOLD}--standard, --s, -standard, -s${NC}               ${GREEN}标准安装${NC}"
    echo -e "    ${DIM}包含: SAGE核心包 + 科学计算库 (numpy, pandas, jupyter)${NC}"
    echo -e "    ${DIM}安装方式: 生产模式安装 (pip install)${NC}"
    echo -e "    ${DIM}适合: 数据科学、研究、学习${NC}"
    echo ""
    echo -e "  ${BOLD}--mini, --minimal, --m, -mini, -minimal, -m${NC}  ${GRAY}最小安装${NC}"
    echo -e "    ${DIM}包含: SAGE核心包 (sage-common, sage-kernel, sage-middleware, sage-libs, sage)${NC}"
    echo -e "    ${DIM}安装方式: 生产模式安装 (pip install)${NC}"
    echo -e "    ${DIM}适合: 容器部署、只需要SAGE核心功能的场景${NC}"
    echo ""
    echo -e "  ${BOLD}--dev, --d, -dev, -d${NC}                         ${YELLOW}开发者安装 (默认)${NC}"
    echo -e "    ${DIM}包含: 标准安装 + 开发工具 (pytest, black, mypy, pre-commit)${NC}"
    echo -e "    ${DIM}安装方式: 开发模式安装 (pip install -e)${NC}"
    echo -e "    ${DIM}适合: 为SAGE项目贡献代码的开发者${NC}"
    echo ""
    
    echo -e "${BLUE}🔧 安装环境 (默认: conda环境)：${NC}"
    echo ""
    echo -e "  ${BOLD}--conda, -conda${NC}                              ${GREEN}使用 conda 环境 (默认)${NC}"
    echo -e "    ${DIM}创建独立的conda环境进行安装${NC}"
    echo -e "    ${DIM}提供最佳的环境隔离和依赖管理${NC}"
    echo ""
    echo -e "  ${BOLD}--pip, -pip${NC}                                  仅使用系统 Python 环境"
    echo -e "    ${DIM}在当前环境中直接使用pip安装${NC}"
    echo ""
    
    echo -e "${BLUE}🤖 AI 模型支持：${NC}"
    echo ""
    echo -e "  ${BOLD}--vllm${NC}                                       ${PURPLE}准备 VLLM 环境${NC}"
    echo -e "    ${DIM}准备 VLLM 使用环境和启动脚本${NC}"
    echo -e "    ${DIM}VLLM 将在首次使用时自动安装（通过 vllm_local_serve.sh）${NC}"
    echo -e "    ${DIM}包含使用指南和推荐模型信息${NC}"
    echo ""
    
    echo -e "${BLUE}💡 使用示例：${NC}"
    echo -e "  ./quickstart.sh                                  ${DIM}# 使用默认设置 (开发者模式 + conda环境)${NC}"
    echo -e "  ./quickstart.sh --standard                       ${DIM}# 标准安装 + conda环境${NC}"
    echo -e "  ./quickstart.sh --minimal --pip                  ${DIM}# 最小安装 + 系统Python环境${NC}"
    echo -e "  ./quickstart.sh --dev --conda                    ${DIM}# 开发者安装 + conda环境${NC}"
    echo -e "  ./quickstart.sh --s --pip                        ${DIM}# 标准安装 + 系统Python环境${NC}"
    echo -e "  ./quickstart.sh --vllm                           ${DIM}# 开发者安装 + 准备 VLLM 环境${NC}"
    echo -e "  ./quickstart.sh --standard --vllm                ${DIM}# 标准安装 + 准备 VLLM 环境${NC}"
    echo ""
}




# 解析安装模式参数
parse_install_mode() {
    local param="$1"
    case "$param" in
        "--standard"|"--s"|"-standard"|"-s")
            INSTALL_MODE="standard"
            return 0
            ;;
        "--mini"|"--minimal"|"--m"|"-mini"|"-minimal"|"-m")
            INSTALL_MODE="minimal"
            return 0
            ;;
        "--dev"|"--d"|"-dev"|"-d")
            INSTALL_MODE="dev"
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析安装环境参数
parse_install_environment() {
    local param="$1"
    case "$param" in
        "--conda"|"-conda")
            INSTALL_ENVIRONMENT="conda"
            return 0
            ;;
        "--pip"|"-pip")
            INSTALL_ENVIRONMENT="pip"
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析 VLLM 参数
parse_vllm_option() {
    local param="$1"
    case "$param" in
        "--vllm"|"-vllm")
            INSTALL_VLLM=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析帮助参数
parse_help_option() {
    local param="$1"
    case "$param" in
        "--help"|"--h"|"-help"|"-h")
            SHOW_HELP=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 主参数解析函数
parse_arguments() {
    local unknown_params=()
    
    # 首先检查是否有帮助参数
    for arg in "$@"; do
        if parse_help_option "$arg"; then
            show_parameter_help
            exit 0
        fi
    done
    
    # 解析其他参数
    while [[ $# -gt 0 ]]; do
        local param="$1"
        
        if parse_install_mode "$param"; then
            # 安装模式参数
            shift
        elif parse_install_environment "$param"; then
            # 安装环境参数
            shift
        elif parse_vllm_option "$param"; then
            # VLLM 安装参数
            shift
        else
            # 未知参数
            unknown_params+=("$param")
            shift
        fi
    done
    
    # 处理未知参数
    if [ ${#unknown_params[@]} -gt 0 ]; then
        echo -e "${CROSS} 发现未知参数: ${unknown_params[*]}"
        echo ""
        show_parameter_help
        exit 1
    fi
    
    # 设置默认值并显示提示
    set_defaults_and_show_tips
}

# 设置默认值并显示提示
set_defaults_and_show_tips() {
    local has_defaults=false
    
    # 设置安装模式默认值
    if [ -z "$INSTALL_MODE" ]; then
        INSTALL_MODE="dev"
        echo -e "${INFO} 未指定安装模式，使用默认: ${YELLOW}开发者模式${NC}"
        has_defaults=true
    fi
    
    # 设置安装环境默认值
    if [ -z "$INSTALL_ENVIRONMENT" ]; then
        INSTALL_ENVIRONMENT="conda"
        echo -e "${INFO} 未指定安装环境，使用默认: ${GREEN}conda环境${NC}"
        has_defaults=true
    fi
    
    # 如果使用了默认值，显示提示
    if [ "$has_defaults" = true ]; then
        echo -e "${DIM}提示: 可使用 --help 查看所有可用选项${NC}"
        echo ""
    fi
    
    # 显示最终配置
    echo -e "${BLUE}📋 安装配置：${NC}"
    case "$INSTALL_MODE" in
        "standard")
            echo -e "  ${BLUE}安装模式:${NC} ${GREEN}标准安装${NC}"
            ;;
        "minimal")
            echo -e "  ${BLUE}安装模式:${NC} ${GRAY}最小安装${NC}"
            ;;
        "dev")
            echo -e "  ${BLUE}安装模式:${NC} ${YELLOW}开发者安装${NC}"
            ;;
    esac
    
    case "$INSTALL_ENVIRONMENT" in
        "conda")
            echo -e "  ${BLUE}安装环境:${NC} ${GREEN}conda环境${NC}"
            ;;
        "pip")
            echo -e "  ${BLUE}安装环境:${NC} ${PURPLE}系统Python环境${NC}"
            ;;
    esac
    
    if [ "$INSTALL_VLLM" = true ]; then
        echo -e "  ${BLUE}AI 模型支持:${NC} ${PURPLE}VLLM${NC}"
    fi
    echo ""
}

# 获取解析后的安装模式
get_install_mode() {
    echo "$INSTALL_MODE"
}

# 获取解析后的安装环境
get_install_environment() {
    echo "$INSTALL_ENVIRONMENT"
}

# 获取是否安装 VLLM
get_install_vllm() {
    echo "$INSTALL_VLLM"
}

# 检查是否需要显示帮助
should_show_help() {
    [ "$SHOW_HELP" = true ]
}
