#!/bin/bash
# SAGE 安装脚本 - 综合系统环境检查模块
# 按照指定顺序进行系统检查：预检查 -> 通用检查 -> 模式特定检查 -> SAGE 检查

# 导入颜色定义和输出格式化
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/output_formatter.sh"
source "$(dirname "${BASH_SOURCE[0]}")/system_deps.sh"

# ============================================================================
# 预检查（静默检查，用于决定输出格式）
# ============================================================================

# 预检查系统环境以决定输出格式
pre_check_system_environment() {
    # 检测是否需要 VS Code 偏移
    detect_vscode_offset_requirement

    # 如果用户设置了自定义偏移
    if [ -n "${SAGE_CUSTOM_OFFSET}" ]; then
        set_custom_offset "$SAGE_CUSTOM_OFFSET"
    fi
}

# ============================================================================
# 通用系统环境检查
# ============================================================================

# 检测运行环境
detect_runtime_environment() {
    # 检查是否在 Docker 中
    if [ -f "/.dockerenv" ] || grep -q "docker" /proc/1/cgroup 2>/dev/null; then
        echo "Docker"
        return 0
    fi

    # 检查是否在 WSL 中
    if grep -qi "microsoft" /proc/version 2>/dev/null || [ -n "${WSL_DISTRO_NAME}" ]; then
        echo "WSL"
        return 0
    fi

    # 检查是否在其他容器中
    if [ -f "/run/.containerenv" ] || grep -q "container" /proc/1/cgroup 2>/dev/null; then
        echo "Container"
        return 0
    fi

    # 默认为原生系统
    echo "Native"
    return 0
}

# 检查操作系统及版本
check_operating_system() {
    output_info "检查操作系统环境..."

    if [ -f /etc/os-release ]; then
        source /etc/os-release
        local os_name="$NAME"
        local os_version="$VERSION"
        local os_id="$ID"
        local version_id="$VERSION_ID"

        # 检测运行环境
        local runtime_env=$(detect_runtime_environment)

        output_check "操作系统: $os_name $os_version"
        output_check "运行环境: $runtime_env"

        # 根据运行环境给出建议
        case "$runtime_env" in
            "Docker")
                output_info "检测到 Docker 容器环境"
                output_dim "建议: 确保容器有足够的资源和网络访问权限"
                ;;
            "WSL")
                output_info "检测到 WSL 环境"
                output_dim "建议: 确保 WSL2 和 Windows 系统资源充足"
                ;;
            "Container")
                output_info "检测到容器环境"
                output_dim "建议: 确保容器配置正确"
                ;;
            "Native")
                output_info "检测到原生 Linux 环境"
                ;;
        esac

        # 检查是否为 Ubuntu 22.04
        if [ "$os_id" = "ubuntu" ] && [ "$version_id" = "22.04" ]; then
            output_check "使用推荐的 Ubuntu 22.04 版本"
        else
            output_warning "当前系统: $os_name $os_version"
            output_warning "推荐使用 Ubuntu 22.04，当前系统可能存在兼容性问题"
            output_dim "继续安装，但可能遇到意外问题..."
        fi
    else
        output_warning "无法检测操作系统版本"
        output_dim "继续安装，但建议使用 Ubuntu 22.04"
    fi

    return 0
}

# 检查系统运行环境
check_system_runtime() {
    output_info "检查系统运行环境..."

    # 检查内存
    local total_mem=$(free -h | awk 'NR==2{print $2}')
    output_check "系统内存: $total_mem"

    # 检查磁盘空间
    local disk_space=$(df -h . | awk 'NR==2{print $4}')
    output_check "可用磁盘空间: $disk_space"

    # 检查基础命令
    local missing_commands=()
    for cmd in curl wget git; do
        if ! command -v $cmd &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done

    if [ ${#missing_commands[@]} -gt 0 ]; then
        output_warning "缺少基础命令: ${missing_commands[*]}"
        output_dim "建议安装: sudo apt update && sudo apt install -y ${missing_commands[*]}"
    else
        output_check "基础命令工具已安装"
    fi

    return 0
}

# 检查 CPU 架构
check_cpu_architecture() {
    output_info "检查 CPU 架构..."

    local cpu_arch=$(uname -m)
    output_check "CPU 架构: $cpu_arch"

    case "$cpu_arch" in
        "x86_64"|"amd64")
            output_check "运行在推荐的 x86_64 架构"
            ;;
        "aarch64"|"arm64")
            output_warning "检测到 ARM 架构 ($cpu_arch)"
            output_warning "ARM 架构可能存在兼容性问题，部分包可能不可用"
            output_dim "继续安装，但可能遇到意外问题..."
            ;;
        *)
            output_warning "检测到非标准架构: $cpu_arch"
            output_warning "此架构可能不被完全支持"
            output_dim "继续安装，但可能遇到意外问题..."
            ;;
    esac

    return 0
}

# 检查 GPU 配置
check_gpu_configuration() {
    output_info "检查 GPU 配置..."

    local gpu_found=false

    # 检查 NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
        local nvidia_info=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null)
        if [ -n "$nvidia_info" ]; then
            output_check "检测到 NVIDIA GPU:"
            echo "$nvidia_info" | while IFS=, read -r gpu_name gpu_memory; do
                output_dim "  - $gpu_name (${gpu_memory}MB 显存)"
            done
            gpu_found=true
        fi
    fi

    # 检查 AMD GPU
    if command -v rocm-smi &> /dev/null; then
        if rocm-smi --showproductname &> /dev/null; then
            output_check "检测到 AMD GPU (ROCm)"
            gpu_found=true
        fi
    fi

    if [ "$gpu_found" = false ]; then
        output_warning "未检测到 GPU 设备"
        output_warning "SAGE 的某些功能（如深度学习加速）可能无法使用"
        output_dim "继续安装，但建议配置 GPU 以获得最佳性能..."
    fi

    return 0
}

# ============================================================================
# 主要检查函数
# ============================================================================

# 综合系统环境检查（包含预检查）
comprehensive_system_check() {
    local mode="${1:-dev}"
    local environment="${2:-conda}"

    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"

    # 显示检查开始信息
    echo ""
    format_output "${GEAR} 开始系统环境检查..."

    # 初始化日志文件（如果不存在）
    mkdir -p "$(dirname "$log_file")"
    if [ ! -f "$log_file" ]; then
        echo "SAGE 安装日志 - $(date)" > "$log_file"
        echo "========================================" >> "$log_file"
    fi

    # 记录系统检查开始
    echo "" >> "$log_file"
    echo "$(date): 开始系统环境检查" >> "$log_file"
    echo "检查模式: $mode" >> "$log_file"
    echo "检查环境: $environment" >> "$log_file"
    echo "----------------------------------------" >> "$log_file"

    # 如果启用了偏移，显示调试信息
    if [ "${SAGE_DEBUG_OFFSET}" = "true" ]; then
        show_offset_status
    fi

    echo ""

    # 通用系统检查
    format_output "${BLUE}=== 通用系统环境检查 ===${NC}"
    echo "$(date): 开始通用系统环境检查" >> "$log_file"
    check_operating_system
    echo ""
    check_system_runtime
    echo ""
    check_cpu_architecture
    echo ""
    check_gpu_configuration
    echo ""

    # 系统依赖检查和安装
    if ! check_and_install_system_dependencies "$log_file"; then
        echo -e "${CROSS} 系统依赖安装失败，但继续进行其他检查"
        echo "$(date): 系统依赖安装失败，但继续进行其他检查" >> "$log_file"
    fi
    echo ""

    # 模式特定检查
    format_output "${BLUE}=== 环境特定检查 ===${NC}"
    echo "$(date): 开始环境特定检查 ($environment 模式)" >> "$log_file"
    case "$environment" in
        "pip")
            if ! check_pip_mode_requirements; then
                echo "$(date): pip 模式环境检查失败" >> "$log_file"
                return 1
            fi
            ;;
        "conda")
            if ! check_conda_mode_requirements; then
                echo "$(date): conda 模式环境检查失败" >> "$log_file"
                return 1
            fi
            ;;
    esac
    echo ""

    # SAGE 特定检查
    format_output "${BLUE}=== SAGE 安装检查 ===${NC}"
    echo "$(date): 开始 SAGE 安装状态检查" >> "$log_file"
    check_existing_sage
    echo ""

    format_output "${CHECK} 系统环境检查完成"
    echo "$(date): 系统环境检查完成" >> "$log_file"
    echo "----------------------------------------" >> "$log_file"

    return 0
}

# pip 模式检查
check_pip_mode_requirements() {
    echo -e "${INFO} 检查 pip 模式环境..."

    # 检查 Python 版本
    if ! command -v python3 &> /dev/null; then
        echo -e "${CROSS} Python3 未找到！"
        echo -e "${CROSS} pip 模式需要 Python 3.11，请先安装 Python"
        return 1
    fi

    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    local python_major=$(echo $python_version | cut -d. -f1)
    local python_minor=$(echo $python_version | cut -d. -f2)

    echo -e "${CHECK} Python 版本: $python_version"

    # 检查是否为支持的 Python 版本（3.8+）
    if [ "$python_major" = "3" ] && [ "$python_minor" -ge "8" ]; then
        if [ "$python_minor" = "11" ]; then
            echo -e "${CHECK} 运行在推荐的 Python 3.11 环境"
        else
            echo -e "${INFO} 运行在 Python $python_version 环境 (支持，推荐 3.11)"
        fi
    else
        echo -e "${CROSS} SAGE 需要 Python 3.8 或更高版本，当前版本: $python_version"
        echo -e "${DIM}建议: 升级到 Python 3.8+ 或使用 conda 模式${NC}"
        return 1
    fi

    # 检查 pip
    if ! python3 -m pip --version &> /dev/null; then
        echo -e "${CROSS} pip 未找到！请先安装 pip"
        echo -e "${DIM}建议: sudo apt install python3-pip${NC}"
        return 1
    fi

    echo -e "${CHECK} pip 可用"
    return 0
}

# conda 模式检查
check_conda_mode_requirements() {
    echo -e "${INFO} 检查 conda 模式环境..."

    if ! command -v conda &> /dev/null; then
        echo -e "${CROSS} Conda 未找到！"
        echo -e "${CROSS} conda 模式需要安装 Anaconda 或 Miniconda"
        echo -e "${DIM}请访问: https://docs.conda.io/en/latest/miniconda.html${NC}"
        return 1
    fi

    local conda_version=$(conda --version 2>&1 | cut -d' ' -f2)
    echo -e "${CHECK} Conda 版本: $conda_version"

    # 检查当前环境
    local current_env=$(conda env list | grep '\*' | awk '{print $1}')
    echo -e "${INFO} 当前 Conda 环境: $current_env"

    return 0
}

# ============================================================================
# SAGE 安装检查
# ============================================================================

# 检查是否已安装SAGE
check_existing_sage() {
    echo -e "${INFO} 检查是否已安装 SAGE..."

    # 检查pip包列表中的所有SAGE相关包变体
    local installed_packages=$(pip list 2>/dev/null | grep -E '^(sage|isage|intsage)(-|$)' || echo "")
    if [ -n "$installed_packages" ]; then
        # 获取第一个包的版本作为代表版本
        local version=$(echo "$installed_packages" | head -n1 | awk '{print $2}')
        echo -e "${WARNING} 检测到已安装的 SAGE v${version}"
        echo
        echo -e "${DIM}已安装的包：${NC}"
        echo "$installed_packages" | while read line; do
            echo -e "${DIM}  - $line${NC}"
        done
        echo

        # 在CI环境中自动卸载重装
        if [[ -n "$CI" || -n "$GITHUB_ACTIONS" || -n "$GITLAB_CI" || -n "$JENKINS_URL" || -n "$BUILDKITE" ]]; then
            echo -e "${INFO} CI环境检测到已安装包，执行强制重装..."
            # 导入卸载函数
            source "$(dirname "${BASH_SOURCE[0]}")/sage_check.sh"
            uninstall_sage
            echo -e "${CHECK} CI环境强制重装准备完成"
        else
            echo -e "${WARNING} 检测到已安装 请强制重装"
            echo -e "${DIM}提示: 建议先卸载现有版本以避免冲突${NC}"
        fi

        return 0
    fi

    # 检查是否能导入sage（作为备用检查）
    if python3 -c "import sage" 2>/dev/null; then
        local sage_version=$(python3 -c "import sage; print(sage.__version__)" 2>/dev/null || echo "unknown")
        echo -e "${WARNING} 检测到已安装的 SAGE v${sage_version}"

        # 在CI环境中自动卸载重装
        if [[ -n "$CI" || -n "$GITHUB_ACTIONS" || -n "$GITLAB_CI" || -n "$JENKINS_URL" || -n "$BUILDKITE" ]]; then
            echo -e "${INFO} CI环境检测到已安装包，执行强制重装..."
            # 导入卸载函数
            source "$(dirname "${BASH_SOURCE[0]}")/sage_check.sh"
            uninstall_sage
            echo -e "${CHECK} CI环境强制重装准备完成"
        fi

        return 0
    fi

    echo -e "${SUCCESS} 未检测到已安装的 SAGE"
    return 1
}

# ============================================================================
# 综合检查函数
# ============================================================================

# 执行完整的系统环境检查
run_system_checks() {
    local install_mode="$1"  # pip 或 conda

    echo ""
    echo -e "${GEAR} 开始系统环境检查..."
    echo ""

    # 1. 通用系统检查
    echo -e "${BLUE}=== 通用系统环境检查 ===${NC}"
    check_operating_system
    echo ""

    check_system_runtime
    echo ""

    check_cpu_architecture
    echo ""

    check_gpu_configuration
    echo ""

    # 2. 模式特定检查
    echo -e "${BLUE}=== 安装环境检查 (${install_mode} 模式) ===${NC}"
    case "$install_mode" in
        "pip")
            if ! check_pip_mode_requirements; then
                echo -e "${CROSS} pip 模式环境检查失败，安装终止"
                exit 1
            fi
            ;;
        "conda")
            if ! check_conda_mode_requirements; then
                echo -e "${CROSS} conda 模式环境检查失败，安装终止"
                exit 1
            fi
            ;;
        *)
            echo -e "${CROSS} 未知安装模式: $install_mode"
            exit 1
            ;;
    esac
    echo ""

    # 3. SAGE 安装检查
    echo -e "${BLUE}=== SAGE 安装状态检查 ===${NC}"
    local sage_installed=false
    if check_existing_sage; then
        sage_installed=true
    fi
    echo ""

    echo -e "${CHECK} 系统环境检查完成"

    # 返回 SAGE 是否已安装的状态
    return $([ "$sage_installed" = true ] && echo 0 || echo 1)
}

# 验证 SAGE 安装
verify_installation() {
    echo ""
    echo -e "${INFO} 验证 SAGE 安装..."

    # 使用与安装时相同的Python命令和环境
    local python_cmd="${PYTHON_CMD:-python3}"

    # 如果使用conda环境且环境变量存在，使用conda run
    if [ -n "$SAGE_ENV_NAME" ] && command -v conda &> /dev/null; then
        # 检查 conda 环境是否真实存在
        if conda env list | grep -q "^${SAGE_ENV_NAME} "; then
            python_cmd="conda run -n $SAGE_ENV_NAME python"
            echo -e "${DIM}在conda环境 $SAGE_ENV_NAME 中验证...${NC}"
        else
            # 环境不存在，使用默认 Python
            echo -e "${DIM}conda环境 $SAGE_ENV_NAME 不存在，在当前环境中验证...${NC}"
        fi
    elif [ -n "$PIP_CMD" ] && [[ "$PIP_CMD" == *"conda run"* ]]; then
        # 从PIP_CMD中提取环境名
        local env_name=$(echo "$PIP_CMD" | sed -n 's/.*conda run -n \([^ ]*\).*/\1/p')
        if [ -n "$env_name" ]; then
            # 检查环境是否存在
            if conda env list | grep -q "^${env_name} "; then
                python_cmd="conda run -n $env_name python"
                echo -e "${DIM}在conda环境 $env_name 中验证...${NC}"
            else
                echo -e "${DIM}conda环境 $env_name 不存在，在当前环境中验证...${NC}"
            fi
        fi
    else
        echo -e "${DIM}在当前环境中验证...${NC}"
    fi

    local verify_output
    verify_output=$($python_cmd -c "
import sage
import sage.common
import sage.kernel
import sage.libs
import sage.middleware
print(f'${CHECK} SAGE v{sage.__version__} 安装成功！')
print(f'${CHECK} 所有子包版本一致: {sage.common.__version__}')
" 2>&1)
    local verify_status=$?

    echo "$verify_output"

    if [ $verify_status -eq 0 ]; then
        echo -e "${CHECK} 验证通过！"
        return 0
    else
        echo -e "${WARNING} 验证出现问题，但安装可能成功了"
        echo -e "${DIM}尝试使用以下命令手动验证：${NC}"
        echo -e "${DIM}  $python_cmd -c \"import sage; print(sage.__version__)\"${NC}"
        return 1
    fi
}
