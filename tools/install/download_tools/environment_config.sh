#!/bin/bash
# SAGE 安装脚本 - 环境配置管理器
# 统一管理安装环境的配置和设置

# 导入颜色定义（必须在最前面）
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 导入 conda 管理工具
source "$(dirname "${BASH_SOURCE[0]}")/conda_manager.sh"

# 尝试通过公网 IP 判断是否位于中国大陆
detect_mainland_china_ip() {
    local detector=""
    if command -v curl >/dev/null 2>&1; then
        detector="curl -s --max-time 3"
    elif command -v wget >/dev/null 2>&1; then
        detector="wget -qO- --timeout=3"
    else
        return 1
    fi

    local endpoints=(
        "https://ipinfo.io/country"
        "https://ifconfig.co/country-iso"
        "https://ipapi.co/country/"
    )

    for url in "${endpoints[@]}"; do
        local code=$($detector "$url" 2>/dev/null | tr -d ' \r\n\t')
        if [[ "$code" =~ ^[A-Z]{2}$ ]]; then
            if [ "$code" = "CN" ]; then
                return 0
            fi
            return 1
        fi
    done

    return 1
}

# 配置 pip 镜像
# 配置 pip 镜像
configure_pip_mirror() {
    local mirror_source="${1:-auto}"

    # 如果设置了 SAGE_FORCE_CHINA_MIRROR=true，强制使用中国镜像（适用于中国的 self-hosted runner）
    if [ "$SAGE_FORCE_CHINA_MIRROR" = "true" ]; then
        export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple/"
        export PIP_EXTRA_INDEX_URL=""
        echo -e "${GREEN}  ✓ SAGE_FORCE_CHINA_MIRROR=true，强制使用清华镜像${NC}"
        return 0
    fi

    # CI环境自动禁用镜像（使用官方PyPI以确保稳定性）
    # 但如果检测到中国大陆 IP，仍然使用镜像加速
    if [ "${CI:-}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ] || [ -n "${JENKINS_URL:-}" ]; then
        # 在 CI 中也尝试检测是否在中国
        if detect_mainland_china_ip; then
            export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple/"
            export PIP_EXTRA_INDEX_URL=""
            echo -e "${GREEN}  ✓ CI环境 + 中国大陆网络检测，使用清华镜像加速${NC}"
            return 0
        fi
        export PIP_INDEX_URL="https://pypi.org/simple/"
        export PIP_EXTRA_INDEX_URL=""
        echo -e "${INFO} CI环境检测：使用官方 PyPI（国际网络）"
        return 0
    fi

    echo -e "${INFO} 配置 pip 镜像: $mirror_source"

    case "$mirror_source" in
        "auto")
            # 自动检测最优镜像，优先根据公网 IP 判断
            if detect_mainland_china_ip; then
                export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple/"
                export PIP_EXTRA_INDEX_URL=""
                echo -e "${GREEN}  ✓ 检测到中国大陆网络，自动使用清华镜像加速${NC}"
            elif [[ "$LANG" == zh_* ]] || [[ "$LC_ALL" == zh_* ]] || [[ "$LC_CTYPE" == zh_* ]]; then
                export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple/"
                export PIP_EXTRA_INDEX_URL=""
                echo -e "${GREEN}  ✓ 检测到中文环境，自动使用清华镜像加速${NC}"
            else
                export PIP_INDEX_URL="https://pypi.org/simple/"
                export PIP_EXTRA_INDEX_URL=""
                echo -e "${DIM}  使用官方 PyPI（国际网络）${NC}"
            fi
            ;;
        "aliyun")
            export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
            export PIP_EXTRA_INDEX_URL=""
            echo -e "${GREEN}  ✓ 使用阿里云镜像${NC}"
            ;;
        "tencent")
            export PIP_INDEX_URL="https://mirrors.cloud.tencent.com/pypi/simple/"
            export PIP_EXTRA_INDEX_URL=""
            echo -e "${GREEN}  ✓ 使用腾讯云镜像${NC}"
            ;;
        "pypi")
            export PIP_INDEX_URL="https://pypi.org/simple/"
            export PIP_EXTRA_INDEX_URL=""
            echo -e "${DIM}  使用官方 PyPI${NC}"
            ;;
        "disable")
            # 显式禁用镜像配置
            unset PIP_INDEX_URL
            unset PIP_EXTRA_INDEX_URL
            echo -e "${DIM}  镜像已禁用${NC}"
            return 0
            ;;
        custom:*)
            local custom_url="${mirror_source#custom:}"
            export PIP_INDEX_URL="$custom_url"
            export PIP_EXTRA_INDEX_URL=""
            echo -e "${GREEN}  ✓ 使用自定义镜像: $custom_url${NC}"
            ;;
        *)
            echo -e "${WARNING} 未知镜像源: $mirror_source，使用官方 PyPI"
            export PIP_INDEX_URL="https://pypi.org/simple/"
            export PIP_EXTRA_INDEX_URL=""
            ;;
    esac

    echo -e "${DIM}  PIP_INDEX_URL: $PIP_INDEX_URL${NC}"
}

# 检测是否在虚拟环境中
detect_virtual_environment() {
    local is_venv=false
    local venv_type=""
    local venv_name=""

    # 检查 conda 环境
    if [ -n "${CONDA_DEFAULT_ENV:-}" ] && [ "${CONDA_DEFAULT_ENV:-}" != "base" ]; then
        is_venv=true
        venv_type="conda"
        venv_name="${CONDA_DEFAULT_ENV:-}"
    elif [ -n "${CONDA_PREFIX:-}" ] && [[ "${CONDA_PREFIX:-}" != *"/base" ]]; then
        is_venv=true
        venv_type="conda"
        venv_name=$(basename "${CONDA_PREFIX:-}")
    fi

    # 检查 Python venv
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        is_venv=true
        venv_type="venv"
        venv_name=$(basename "${VIRTUAL_ENV:-}")
    fi

    echo "$is_venv|$venv_type|$venv_name"
}

# 检查虚拟环境隔离（可配置为警告或错误）
check_virtual_environment_isolation() {
    local install_environment="$1"
    local auto_venv="${2:-false}"

    # 如果用户选择了 conda，则会创建新环境，不需要额外检查
    if [ "$install_environment" = "conda" ]; then
        return 0
    fi

    # CI 环境跳过检查
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${GITLAB_CI:-}" || -n "${JENKINS_URL:-}" ]]; then
        return 0
    fi

    local venv_info=$(detect_virtual_environment)
    local is_venv=$(echo "$venv_info" | cut -d'|' -f1)
    local venv_type=$(echo "$venv_info" | cut -d'|' -f2)
    local venv_name=$(echo "$venv_info" | cut -d'|' -f3)

    if [ "$is_venv" = "false" ]; then
        # 如果启用了 auto-venv，自动创建虚拟环境
        if [ "$auto_venv" = "true" ]; then
            echo ""
            echo -e "${BLUE}🔧 自动创建虚拟环境${NC}"
            echo ""

            local venv_path=".sage/venv"
            echo -e "${INFO} 将在 ${GREEN}$venv_path${NC} 创建 Python 虚拟环境"

            if ! ensure_python_venv "$venv_path"; then
                echo -e "${RED}错误: 无法自动创建虚拟环境${NC}"
                echo -e "${DIM}请手动创建: python3 -m venv $venv_path${NC}"
                exit 1
            fi

            source "$venv_path/bin/activate"
            if [ -n "${VIRTUAL_ENV:-}" ]; then
                echo -e "${CHECK} 虚拟环境已激活: ${GREEN}$venv_path${NC}"
                export PIP_CMD="python3 -m pip"
                export PYTHON_CMD="python3"
                return 0
            fi
        fi

        # 读取配置（默认为 warning）
        local venv_policy="${SAGE_VENV_POLICY:-warning}"

        echo ""
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}⚠️  环境隔离警告${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${WARNING} 检测到您正在使用系统 Python 环境（非虚拟环境）"
        echo ""
        echo -e "${BLUE}为什么推荐使用虚拟环境？${NC}"
        echo -e "  ${DIM}• 避免与系统包冲突${NC}"
        echo -e "  ${DIM}• 保持系统环境清洁${NC}"
        echo -e "  ${DIM}• 便于完全卸载和清理${NC}"
        echo -e "  ${DIM}• 隔离不同项目的依赖${NC}"
        echo ""

        echo -e "${BLUE}建议的操作：${NC}"
        echo ""
        echo -e "  ${YELLOW}1. 自动创建虚拟环境（推荐）${NC}"
        echo -e "     ${DIM}重新运行: ${CYAN}./quickstart.sh --auto-venv${NC}"
        echo ""
        echo -e "  ${PURPLE}2. 手动创建虚拟环境${NC}"
        echo -e "     ${DIM}使用 conda: ${CYAN}./quickstart.sh --conda${NC}"
        echo -e "     ${DIM}或使用 venv: ${CYAN}python3 -m venv .sage/venv && source .sage/venv/bin/activate${NC}"
        echo ""
        echo -e "  ${GRAY}3. 继续在系统环境中安装（不推荐）${NC}"
        echo -e "     ${DIM}风险：可能污染系统 Python 环境${NC}"
        echo ""

        # 根据策略处理
        case "$venv_policy" in
            "error")
                echo -e "${RED}${BOLD}✗ 错误：必须使用虚拟环境${NC}"
                echo ""
                echo -e "${DIM}配置环境变量可修改此行为：${NC}"
                echo -e "${DIM}  export SAGE_VENV_POLICY=warning  # 改为警告${NC}"
                echo -e "${DIM}  export SAGE_VENV_POLICY=ignore   # 忽略检查${NC}"
                echo ""
                echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                exit 1
                ;;
            "warning")
                echo -e "${INFO} 当前策略: ${YELLOW}警告模式${NC}"
                echo ""
                read -p "是否继续在系统环境中安装？[y/N]: " -r continue_choice
                if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
                    echo ""
                    echo -e "${INFO} 安装已取消"
                    echo -e "${DIM}提示: 使用 --auto-venv 可自动创建虚拟环境${NC}"
                    echo ""
                    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                    exit 0
                fi
                echo ""
                echo -e "${WARNING} 将在系统环境中继续安装..."
                echo ""
                echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                ;;
            "ignore")
                echo -e "${DIM}注意: 虚拟环境检查已禁用 (SAGE_VENV_POLICY=ignore)${NC}"
                echo ""
                echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                ;;
            *)
                echo -e "${WARNING} 未知策略: $venv_policy，使用默认警告模式"
                echo ""
                echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                ;;
        esac
    else
        echo -e "${CHECK} 检测到虚拟环境: ${GREEN}$venv_type ($venv_name)${NC}"
    fi

    return 0
}

ensure_python_venv() {
    local venv_path="$1"
    : > /tmp/venv.log
    if python3 -m venv "$venv_path" 2>/tmp/venv.log; then
        return 0
    fi
    echo -e "${DIM}标准 venv 创建失败，尝试使用 virtualenv 模块...${NC}"
    if python3 -m virtualenv "$venv_path" 2>>/tmp/venv.log; then
        return 0
    fi
    echo -e "${DIM}virtualenv 模块不可用，尝试安装...${NC}"
    if python3 -m pip install --user --break-system-packages virtualenv >/tmp/venv.log 2>&1; then
        if python3 -m virtualenv "$venv_path" 2>>/tmp/venv.log; then
            return 0
        fi
    fi
    if [ -f /tmp/venv.log ]; then
        tail -n 20 /tmp/venv.log
    fi
    return 1
}

# 配置安装环境的主函数
configure_installation_environment() {
    local install_environment="${1:-conda}"
    local install_mode="${2:-dev}"
    local conda_env_name="${3:-}"  # 可选的conda环境名

    # CI环境和远程部署的特殊处理
    if [ "${CI:-}" = "true" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ] || [ -n "${JENKINS_URL:-}" ]; then
        # CI环境：不设置PYTHONNOUSERSITE以提高测试速度，但仍保持用户选择的安装环境
        echo -e "${INFO} CI环境中跳过PYTHONNOUSERSITE设置以提高测试速度"
    elif [ "${SAGE_REMOTE_DEPLOY:-}" = "true" ]; then
        # 远程部署环境：设置PYTHONNOUSERSITE以避免包冲突
        export PYTHONNOUSERSITE=1
        echo -e "${INFO} 远程部署环境已设置 PYTHONNOUSERSITE=1 以避免用户包冲突"
    else
        # 本地开发环境：设置PYTHONNOUSERSITE以避免包冲突
        export PYTHONNOUSERSITE=1
        echo -e "${INFO} 已设置 PYTHONNOUSERSITE=1 以避免用户包冲突"
    fi

    # 检查虚拟环境隔离（--auto-venv 会在 argument_parser 中设置 SAGE_AUTO_VENV）
    check_virtual_environment_isolation "$install_environment" "${SAGE_AUTO_VENV:-false}"

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
            # 清除 SAGE_ENV_NAME 以避免验证脚本尝试使用不存在的 conda 环境
            export SAGE_ENV_NAME=""
            ;;
        *)
            echo -e "${CROSS} 未知的安装环境: $install_environment"
            exit 1
            ;;
    esac

    # 设置默认命令（如果没有设置 conda 环境）
    export PIP_CMD="${PIP_CMD:-python3 -m pip}"
    export PYTHON_CMD="${PYTHON_CMD:-python3}"

    # 智能配置 pip 镜像（自动检测CI环境和网络环境）
    # CI环境自动禁用；中国网络自动启用清华镜像
    if [ "${USE_PIP_MIRROR:-true}" = "true" ]; then
        configure_pip_mirror "${MIRROR_SOURCE:-auto}"
    else
        echo -e "${DIM}  pip 镜像已手动禁用（使用 --no-mirror 参数）${NC}"
    fi

    echo -e "${CHECK} 环境配置完成"
}
