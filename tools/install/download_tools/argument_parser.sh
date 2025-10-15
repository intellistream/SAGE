#!/bin/bash
# SAGE 安装脚本 - 参数解析模块
# 处理命令行参数的解析和验证

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 全局变量
INSTALL_MODE=""
INSTALL_ENVIRONMENT=""
INSTALL_VLLM=false
AUTO_CONFIRM=false
SHOW_HELP=false
CLEAN_PIP_CACHE=true
RUN_DOCTOR=false
DOCTOR_ONLY=false
FIX_ENVIRONMENT=false
SYNC_SUBMODULES=""
SYNC_SUBMODULES_EXPLICIT=false
SYNC_SUBMODULES_NOTIFIED=false

# 检测当前Python环境
detect_current_environment() {
    local env_type="system"
    local env_name=""
    local in_conda=false
    local in_venv=false
    
    # 检测conda环境
    if [ -n "$CONDA_DEFAULT_ENV" ] && [ "$CONDA_DEFAULT_ENV" != "base" ]; then
        env_type="conda"
        env_name="$CONDA_DEFAULT_ENV"
        in_conda=true
    elif [ -n "$CONDA_PREFIX" ] && [[ "$CONDA_PREFIX" != *"/base" ]]; then
        env_type="conda"
        env_name=$(basename "$CONDA_PREFIX")
        in_conda=true
    fi
    
    # 检测虚拟环境
    if [ -n "$VIRTUAL_ENV" ]; then
        if [ "$in_conda" = false ]; then
            env_type="venv"
            env_name=$(basename "$VIRTUAL_ENV")
            in_venv=true
        fi
    fi
    
    echo "$env_type|$env_name|$in_conda|$in_venv"
}

# 根据当前环境智能推荐安装方式
get_smart_environment_recommendation() {
    local env_info=$(detect_current_environment)
    local env_type=$(echo "$env_info" | cut -d'|' -f1)
    local env_name=$(echo "$env_info" | cut -d'|' -f2)
    local in_conda=$(echo "$env_info" | cut -d'|' -f3)
    local in_venv=$(echo "$env_info" | cut -d'|' -f4)
    
    if [ "$in_conda" = true ] || [ "$in_venv" = true ]; then
        # 用户已经在虚拟环境中，推荐直接使用
        echo "pip|$env_type|$env_name"
    else
        # 用户在系统环境中，推荐创建conda环境（如果conda可用）
        if command -v conda &> /dev/null; then
            echo "conda|system|"
        else
            echo "pip|system|"
        fi
    fi
}

# 交互式安装菜单
show_installation_menu() {
    echo ""
    echo -e "${BLUE}🔧 请选择安装配置${NC}"
    echo ""
    
    # 选择安装模式
    while true; do
        echo -e "${BOLD}1. 选择安装模式：${NC}"
        echo -e "  ${GREEN}1)${NC} 标准安装    - common + kernel + middleware + libs + 数据科学库"
        echo -e "  ${GRAY}2)${NC} 最小安装    - common + kernel (仅核心功能)"
        echo -e "  ${YELLOW}3)${NC} 开发者安装  - 标准安装 + tools + 开发工具 ${DIM}(推荐)${NC}"
        echo ""
        read -p "请选择安装模式 [1-3，默认3]: " mode_choice
        
        case "${mode_choice:-3}" in
            1)
                INSTALL_MODE="standard"
                break
                ;;
            2)
                INSTALL_MODE="minimal"
                break
                ;;
            3)
                INSTALL_MODE="dev"
                break
                ;;
            *)
                echo -e "${RED}无效选择，请输入 1、2 或 3${NC}"
                echo ""
                ;;
        esac
    done
    
    echo ""
    
    # 检测当前环境并智能推荐
    local recommendation=$(get_smart_environment_recommendation)
    local recommended_env=$(echo "$recommendation" | cut -d'|' -f1)
    local current_env_type=$(echo "$recommendation" | cut -d'|' -f2)
    local current_env_name=$(echo "$recommendation" | cut -d'|' -f3)
    
    # 显示当前环境信息
    if [ "$current_env_type" = "conda" ] && [ -n "$current_env_name" ]; then
        echo -e "${INFO} 检测到您当前在 conda 环境中: ${GREEN}$current_env_name${NC}"
    elif [ "$current_env_type" = "venv" ] && [ -n "$current_env_name" ]; then
        echo -e "${INFO} 检测到您当前在虚拟环境中: ${GREEN}$current_env_name${NC}"
    elif [ "$current_env_type" = "system" ]; then
        echo -e "${INFO} 检测到您当前在系统 Python 环境中"
    fi
    
    echo ""
    
    # 选择安装环境
    while true; do
        echo -e "${BOLD}2. 选择安装环境：${NC}"
        
        if [ "$recommended_env" = "pip" ]; then
            # 推荐使用当前环境
            echo -e "  ${PURPLE}1)${NC} 使用当前环境 ${DIM}(推荐，已在虚拟环境中)${NC}"
            echo -e "  ${GREEN}2)${NC} 创建新的 Conda 环境"
            local default_choice=1
        else
            # 推荐创建conda环境
            echo -e "  ${GREEN}1)${NC} 创建新的 Conda 环境 ${DIM}(推荐)${NC}"
            echo -e "  ${PURPLE}2)${NC} 使用当前系统环境"
            local default_choice=1
        fi
        
        echo ""
        read -p "请选择安装环境 [1-2，默认$default_choice]: " env_choice
        
        case "${env_choice:-$default_choice}" in
            1)
                if [ "$recommended_env" = "pip" ]; then
                    INSTALL_ENVIRONMENT="pip"
                else
                    INSTALL_ENVIRONMENT="conda"
                fi
                break
                ;;
            2)
                if [ "$recommended_env" = "pip" ]; then
                    INSTALL_ENVIRONMENT="conda"
                else
                    INSTALL_ENVIRONMENT="pip"
                fi
                break
                ;;
            *)
                echo -e "${RED}无效选择，请输入 1 或 2${NC}"
                echo ""
                ;;
        esac
    done
    
    echo ""
    
    # 选择是否安装 VLLM
    echo -e "${BOLD}3. AI 模型支持：${NC}"
    echo -e "  是否配置 VLLM 运行环境？${DIM}(用于本地大语言模型推理，配置系统依赖)${NC}"
    echo -e "  ${DIM}注意: VLLM Python包已包含在标准/开发者安装中${NC}"
    echo ""
    read -p "配置 VLLM 环境？[y/N]: " vllm_choice
    
    if [[ $vllm_choice =~ ^[Yy]$ ]]; then
        INSTALL_VLLM=true
    else
        INSTALL_VLLM=false
    fi
    refresh_sync_submodule_default
}

# 显示参数帮助信息
show_parameter_help() {
    echo ""
    echo -e "${BOLD}SAGE 快速安装脚本${NC}"
    echo ""
    echo -e "${BLUE}用法：${NC}"
    echo -e "  ./quickstart.sh                                  ${DIM}# 交互式安装（推荐新用户）${NC}"
    echo -e "  ./quickstart.sh [安装模式] [安装环境] [AI模型支持] [选项]"
    echo ""
    echo -e "${PURPLE}💡 无参数运行时将显示交互式菜单，引导您完成安装配置${NC}"
    echo ""
    
    echo -e "${BLUE}📦 安装模式 (默认: 开发者模式)：${NC}"
    echo ""
    echo -e "  ${BOLD}--standard, --s, -standard, -s${NC}               ${GREEN}标准安装${NC}"
    echo -e "    ${DIM}包含: common + kernel + middleware + libs + 数据科学库${NC}"
    echo -e "    ${DIM}安装方式: 生产模式安装 (pip install)${NC}"
    echo -e "    ${DIM}适合: 数据科学、研究、学习${NC}"
    echo ""
    echo -e "  ${BOLD}--mini, --minimal, --m, -mini, -minimal, -m${NC}  ${GRAY}最小安装${NC}"
    echo -e "    ${DIM}包含: common + kernel (仅核心功能)${NC}"
    echo -e "    ${DIM}安装方式: 生产模式安装 (pip install)${NC}"
    echo -e "    ${DIM}适合: 容器部署、只需要SAGE核心功能的场景${NC}"
    echo ""
    echo -e "  ${BOLD}--dev, --d, -dev, -d${NC}                         ${YELLOW}开发者安装 (默认)${NC}"
    echo -e "    ${DIM}包含: 标准安装 + tools + 开发工具 (pytest, black, mypy, pre-commit)${NC}"
    echo -e "    ${DIM}安装方式: 开发模式安装 (pip install -e)${NC}"
    echo -e "    ${DIM}适合: 为SAGE项目贡献代码的开发者${NC}"
    echo -e "    ${DIM}自动安装: C++扩展 (sage_db, sage_flow) - 需要构建工具${NC}"
    echo ""
    
    echo -e "${BLUE}🔧 安装环境：${NC}"
    echo ""
    echo -e "  ${BOLD}--pip, -pip${NC}                                  ${PURPLE}使用当前环境${NC}"
    echo -e "  ${BOLD}--conda, -conda${NC}                              ${GREEN}创建conda环境${NC}"
    echo ""
    echo -e "  ${DIM}💡 不指定时自动智能选择: 虚拟环境→pip，系统环境→conda${NC}"
    echo ""
    
    echo -e "${BLUE}🤖 AI 模型支持：${NC}"
    echo ""
    echo -e "  ${BOLD}--vllm${NC}                                       ${PURPLE}配置 VLLM 运行环境${NC}"
    echo -e "    ${DIM}与其他模式组合使用，例如: --dev --vllm${NC}"
    echo -e "    ${DIM}配置 CUDA、系统依赖和启动脚本${NC}"
    echo -e "    ${DIM}注意: Python包已包含在标准安装中${NC}"
    echo -e "    ${DIM}包含使用指南和推荐模型信息${NC}"
    echo ""
    
    echo -e "${BLUE}⚡ 其他选项：${NC}"
    echo ""
    echo -e "  ${BOLD}--yes, --y, -yes, -y${NC}                        ${CYAN}跳过确认提示${NC}"
    echo -e "    ${DIM}自动确认所有安装选项，适合自动化脚本${NC}"
    echo ""
    echo -e "  ${BOLD}--sync-submodules${NC}                          ${GREEN}安装前自动同步 submodules${NC}"
    echo -e "    ${DIM}开发者模式默认启用，可用 --no-sync-submodules 跳过${NC}"
    echo ""
    echo -e "  ${BOLD}--doctor, --diagnose, --check-env${NC}           ${GREEN}环境诊断${NC}"
    echo -e "    ${DIM}全面检查 Python 环境、包管理器、依赖等问题${NC}"
    echo -e "    ${DIM}识别并报告常见的环境配置问题${NC}"
    echo ""
    echo -e "  ${BOLD}--doctor-fix, --diagnose-fix, --fix-env${NC}     ${YELLOW}诊断并修复${NC}"
    echo -e "    ${DIM}在诊断的基础上自动修复检测到的问题${NC}"
    echo -e "    ${DIM}安全的自动修复常见环境冲突${NC}"
    echo ""
    echo -e "  ${BOLD}--pre-check, --env-check${NC}                    ${BLUE}安装前检查${NC}"
    echo -e "    ${DIM}在正常安装前进行环境预检查${NC}"
    echo -e "    ${DIM}与其他安装选项结合使用${NC}"
    echo ""
    echo -e "  ${BOLD}--no-cache-clean, --skip-cache-clean${NC}        ${YELLOW}跳过 pip 缓存清理${NC}"
    echo -e "    ${DIM}默认安装前会清理 pip 缓存，此选项可跳过${NC}"
    echo -e "    ${DIM}适用于网络受限或缓存清理可能出错的环境${NC}"
    echo ""
    
    echo -e "${BLUE}💡 使用示例：${NC}"
    echo -e "  ./quickstart.sh                                  ${DIM}# 交互式安装${NC}"
    echo -e "  ./quickstart.sh --dev                            ${DIM}# 开发者安装 + 智能环境选择${NC}"
    echo -e "  ./quickstart.sh --standard --conda               ${DIM}# 标准安装 + conda环境${NC}"
    echo -e "  ./quickstart.sh --minimal --pip --yes            ${DIM}# 最小安装 + 当前环境 + 跳过确认${NC}"
    echo -e "  ./quickstart.sh --dev --vllm --yes               ${DIM}# 开发者安装 + VLLM支持 + 跳过确认${NC}"
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

# 解析自动确认参数
parse_auto_confirm() {
    local param="$1"
    case "$param" in
        "--yes"|"--y"|"-yes"|"-y")
            AUTO_CONFIRM=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

parse_sync_submodules_option() {
    local param="$1"
    case "$param" in
        "--sync-submodules")
            SYNC_SUBMODULES="true"
            SYNC_SUBMODULES_EXPLICIT=true
            return 0
            ;;
        "--no-sync-submodules"|"--skip-submodules")
            SYNC_SUBMODULES="false"
            SYNC_SUBMODULES_EXPLICIT=true
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 解析 pip 缓存清理参数
parse_cache_option() {
    local param="$1"
    case "$param" in
        "--no-cache-clean"|"--skip-cache-clean"|"-no-cache"|"-skip-cache")
            CLEAN_PIP_CACHE=false
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

# 解析环境医生参数
parse_doctor_option() {
    local param="$1"
    case "$param" in
        "--doctor"|"--diagnose"|"--check-env")
            RUN_DOCTOR=true
            DOCTOR_ONLY=true
            return 0
            ;;
        "--doctor-fix"|"--diagnose-fix"|"--fix-env")
            RUN_DOCTOR=true
            FIX_ENVIRONMENT=true
            DOCTOR_ONLY=true
            return 0
            ;;
        "--pre-check"|"--env-check")
            RUN_DOCTOR=true
            DOCTOR_ONLY=false
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
        elif parse_auto_confirm "$param"; then
            # 自动确认参数
            shift
        elif parse_sync_submodules_option "$param"; then
            # 同步 submodule 参数
            shift
        elif parse_cache_option "$param"; then
            # pip 缓存清理参数
            shift
        elif parse_doctor_option "$param"; then
            # 环境医生参数
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
set_default_sync_submodules() {
    if [ "$SYNC_SUBMODULES_EXPLICIT" = true ]; then
        return
    fi

    local desired="false"
    if [ "$INSTALL_MODE" = "dev" ]; then
        desired="true"
    fi

    if [ -z "$SYNC_SUBMODULES" ] || [ "$SYNC_SUBMODULES" != "$desired" ]; then
        SYNC_SUBMODULES="$desired"

        if [ "$desired" = "true" ] && [ "$SYNC_SUBMODULES_NOTIFIED" = false ]; then
            echo -e "${INFO} 开发者模式默认会同步所有 submodules"
            SYNC_SUBMODULES_NOTIFIED=true
        fi
    fi
}

refresh_sync_submodule_default() {
    set_default_sync_submodules
}

set_defaults_and_show_tips() {
    local has_defaults=false
    
    # 检测 CI 环境并自动设置为确认模式
    if [[ -n "$CI" || -n "$GITHUB_ACTIONS" || -n "$GITLAB_CI" || -n "$JENKINS_URL" || -n "$BUILDKITE" ]]; then
        AUTO_CONFIRM=true
        echo -e "${INFO} 检测到 CI 环境，自动启用确认模式"
        has_defaults=true
        
        # CI 环境中的环境选择逻辑
        if [ "$INSTALL_ENVIRONMENT" = "conda" ] && ! command -v conda &> /dev/null; then
            # CI 环境中强制使用 conda 但 conda 不可用时，自动降级到 pip
            echo -e "${WARNING} CI环境中指定了conda但未找到conda，自动降级为pip模式"
            INSTALL_ENVIRONMENT="pip"
            has_defaults=true
        elif [ -z "$INSTALL_ENVIRONMENT" ] && ! command -v conda &> /dev/null; then
            # CI 环境中没有指定环境且没有 conda 时，使用 pip
            INSTALL_ENVIRONMENT="pip"
            echo -e "${INFO} CI环境中未找到conda，自动使用pip模式"
            has_defaults=true
        fi
        
        # 检查是否在受管理的Python环境中（如Ubuntu 24.04+）
        if [ "$INSTALL_ENVIRONMENT" = "pip" ] || [ -z "$INSTALL_ENVIRONMENT" ]; then
            if python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))" 2>/dev/null | grep -q "/usr/lib/python"; then
                echo -e "${WARNING} 检测到受管理的Python环境，在CI中推荐使用--break-system-packages"
                echo -e "${INFO} 这在CI环境中是安全的，因为CI环境是临时的"
            fi
        fi
    fi
    
    # 设置安装模式默认值
    if [ -z "$INSTALL_MODE" ]; then
        INSTALL_MODE="dev"
        echo -e "${INFO} 未指定安装模式，使用默认: ${YELLOW}开发者模式${NC}"
        has_defaults=true
    fi

    # 根据当前安装模式决定是否同步 submodule
    set_default_sync_submodules
    
    # 设置安装环境默认值（基于当前环境智能选择）
    if [ -z "$INSTALL_ENVIRONMENT" ]; then
        local recommendation=$(get_smart_environment_recommendation)
        local recommended_env=$(echo "$recommendation" | cut -d'|' -f1)
        local current_env_type=$(echo "$recommendation" | cut -d'|' -f2)
        local current_env_name=$(echo "$recommendation" | cut -d'|' -f3)
        
        INSTALL_ENVIRONMENT="$recommended_env"
        
        if [ "$recommended_env" = "pip" ] && [ "$current_env_type" != "system" ]; then
            echo -e "${INFO} 检测到虚拟环境，使用默认: ${PURPLE}当前环境 ($current_env_type: $current_env_name)${NC}"
        elif [ "$recommended_env" = "conda" ]; then
            echo -e "${INFO} 检测到系统环境，推荐默认: ${GREEN}创建conda环境${NC}"
        else
            echo -e "${INFO} 未指定安装环境，使用默认: ${PURPLE}系统Python环境${NC}"
        fi
        has_defaults=true
    fi
    
    # 如果使用了默认值，显示提示
    if [ "$has_defaults" = true ]; then
        echo -e "${DIM}提示: 可使用 --help 查看所有可用选项${NC}"
        echo ""
    fi
}

# 显示安装配置信息
show_install_configuration() {
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
            # 检查是否在虚拟环境中
            local current_env_info=$(detect_current_environment)
            local env_type=$(echo "$current_env_info" | cut -d'|' -f1)
            local env_name=$(echo "$current_env_info" | cut -d'|' -f2)
            
            if [ "$env_type" != "system" ]; then
                echo -e "  ${BLUE}安装环境:${NC} ${PURPLE}当前环境 ($env_type: $env_name)${NC}"
            else
                echo -e "  ${BLUE}安装环境:${NC} ${PURPLE}系统Python环境${NC}"
            fi
            ;;
    esac
    
    if [ "$INSTALL_VLLM" = true ]; then
        echo -e "  ${BLUE}AI 模型支持:${NC} ${PURPLE}VLLM${NC}"
    fi

    if [ "$SYNC_SUBMODULES" = "true" ]; then
        echo -e "  ${BLUE}Submodules:${NC} ${GREEN}自动同步${NC}"
    else
        echo -e "  ${BLUE}Submodules:${NC} ${DIM}跳过自动同步${NC}"
    fi
    
    if [ "$CLEAN_PIP_CACHE" = false ]; then
        echo -e "  ${BLUE}特殊选项:${NC} ${YELLOW}跳过 pip 缓存清理${NC}"
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

# 获取是否自动确认
get_auto_confirm() {
    echo "$AUTO_CONFIRM"
}

# 获取是否清理 pip 缓存
get_clean_pip_cache() {
    echo "$CLEAN_PIP_CACHE"
}

# 检查是否需要显示帮助
should_show_help() {
    [ "$SHOW_HELP" = true ]
}

# 获取是否运行环境医生
get_run_doctor() {
    echo "$RUN_DOCTOR"
}

# 获取是否仅运行医生模式
get_doctor_only() {
    echo "$DOCTOR_ONLY"
}

# 获取是否修复环境
get_fix_environment() {
    echo "$FIX_ENVIRONMENT"
}

# 获取是否自动同步 submodules
get_sync_submodules() {
    echo "${SYNC_SUBMODULES:-false}"
}
