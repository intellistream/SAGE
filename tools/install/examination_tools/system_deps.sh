#!/bin/bash
# SAGE 系统依赖管理模块
# 集成到quickstart.sh架构中的系统依赖检查和安装

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"


# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${SAGE_ROOT:-}" ]; then
    SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi

# 导入 Conda 和进度工具
if [ -f "${SAGE_ROOT:-}/tools/lib/conda_install_utils.sh" ]; then
    source "${SAGE_ROOT:-}/tools/lib/conda_install_utils.sh"
fi

if [ -f "${SAGE_ROOT:-}/tools/lib/progress_utils.sh" ]; then
    source "${SAGE_ROOT:-}/tools/lib/progress_utils.sh"
fi

if [ -f "${SAGE_ROOT:-}/tools/conda/conda_utils.sh" ]; then
    source "${SAGE_ROOT:-}/tools/conda/conda_utils.sh"
fi

# 检测操作系统
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        VER=$(lsb_release -sr)
    elif [[ -f /etc/redhat-release ]]; then
        OS="centos"
    elif [[ -f /etc/debian_version ]]; then
        OS="debian"
    else
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    fi
}

# 检查并安装基础构建工具
check_and_install_build_tools() {
    log_info "检查基础构建工具..." "SysDeps"
    echo -e "${INFO} 检查基础构建工具...${NC}"

    # 检查必需的构建工具
    local missing_tools=()

    if ! command -v gcc &> /dev/null; then
        missing_tools+=("gcc")
    fi

    if ! command -v cmake &> /dev/null; then
        missing_tools+=("cmake")
    fi

    if ! command -v make &> /dev/null; then
        missing_tools+=("make")
    fi

    if ! command -v pkg-config &> /dev/null; then
        missing_tools+=("pkg-config")
    fi

    # 检查 Node.js 和 npm (Studio 需要)
    local need_node=false
    if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
        need_node=true
    fi

    # 优先尝试 Conda 安装 (无需 sudo)
    if [ "$need_node" = "true" ] && command -v conda &> /dev/null; then
        log_info "尝试使用 Conda 安装 Node.js (无需 sudo)..." "SysDeps"
        echo -e "${GEAR} 尝试使用 Conda 安装 Node.js..."

        # 使用统一的 conda_install_with_progress 函数
        if conda_install_with_progress "安装 Node.js" nodejs; then
            need_node=false
        else
            log_warn "Conda 安装 Node.js 失败，将尝试系统安装" "SysDeps"
        fi
    fi

    if [ "$need_node" = "true" ]; then
        if ! command -v node &> /dev/null; then missing_tools+=("nodejs"); fi
        if ! command -v npm &> /dev/null; then missing_tools+=("npm"); fi
    fi

    if [ ${#missing_tools[@]} -eq 0 ]; then
        log_info "基础构建工具已安装" "SysDeps"
        echo -e "${CHECK} 基础构建工具已安装"
        return 0
    fi

    log_warn "缺少构建工具: ${missing_tools[*]}" "SysDeps"
    echo -e "${WARNING} 缺少构建工具: ${missing_tools[*]}"

    # 确定sudo权限
    local SUDO=""
    if [[ "${CI:-false}" == "true" ]]; then
        SUDO="sudo"
    elif [[ $EUID -eq 0 ]]; then
        SUDO=""
    elif command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        log_error "需要root权限安装系统依赖，但未找到sudo" "SysDeps"
        echo -e "${CROSS} 需要root权限安装系统依赖，但未找到sudo"
        return 1
    fi

    log_info "安装基础构建工具..." "SysDeps"
    echo -e "${GEAR} 安装基础构建工具（这可能需要几分钟，请耐心等待）...${NC}"

    case "$OS" in
        ubuntu|debian)
            log_command "SysDeps" "Install" "$SUDO apt-get update -qq"

            # 动态构建包列表
            local PKG_LIST="build-essential cmake pkg-config"
            if [[ " ${missing_tools[*]} " =~ " nodejs " ]] || [[ " ${missing_tools[*]} " =~ " npm " ]]; then
                PKG_LIST="$PKG_LIST nodejs npm"
            fi

            # 使用带进度显示的安装
            echo -e "${DIM}正在安装: $PKG_LIST${NC}"
            if long_task_with_keepalive "安装系统依赖" 30 $SUDO apt-get install -y --no-install-recommends $PKG_LIST; then
                log_info "系统依赖安装成功" "SysDeps"
                echo -e "${CHECK} 系统依赖安装成功"
            else
                log_error "系统依赖安装失败" "SysDeps"
                echo -e "${CROSS} 系统依赖安装失败"
                return 1
            fi
            ;;
        centos|rhel)
            local EXTRA_PKGS="cmake pkg-config"
            if [[ " ${missing_tools[*]} " =~ " nodejs " ]] || [[ " ${missing_tools[*]} " =~ " npm " ]]; then
                EXTRA_PKGS="$EXTRA_PKGS nodejs npm"
            fi

            echo -e "${DIM}正在安装开发工具组和额外包...${NC}"
            if command -v dnf &> /dev/null; then
                long_task_with_keepalive "安装开发工具组" 30 $SUDO dnf groupinstall -y 'Development Tools'
                long_task_with_keepalive "安装额外依赖" 30 $SUDO dnf install -y $EXTRA_PKGS
            else
                long_task_with_keepalive "安装开发工具组" 30 $SUDO yum groupinstall -y 'Development Tools'
                long_task_with_keepalive "安装额外依赖" 30 $SUDO yum install -y $EXTRA_PKGS
            fi
            ;;
        fedora)
            local EXTRA_PKGS="cmake pkg-config"
            if [[ " ${missing_tools[*]} " =~ " nodejs " ]] || [[ " ${missing_tools[*]} " =~ " npm " ]]; then
                EXTRA_PKGS="$EXTRA_PKGS nodejs npm"
            fi
            log_command "SysDeps" "Install" "$SUDO dnf groupinstall -y 'Development Tools'"
            log_command "SysDeps" "Install" "$SUDO dnf install -y $EXTRA_PKGS"
            ;;
        arch|manjaro)
            log_command "SysDeps" "Install" "$SUDO pacman -S --noconfirm base-devel cmake pkg-config"
            ;;
        *)
            log_warn "未知操作系统: $OS，请手动安装构建工具" "SysDeps"
            echo -e "${WARNING} 未知操作系统: $OS，请手动安装构建工具"
            return 1
            ;;
    esac

    return 0
}

# 检查并安装数学库 (BLAS/LAPACK)
check_and_install_math_libraries() {
    log_info "检查数学库 (BLAS/LAPACK)..." "SysDeps"
    echo -e "${INFO} 检查数学库 (BLAS/LAPACK)...${NC}"

    # 检查库文件是否存在
    local BLAS_FOUND=false
    local LAPACK_FOUND=false

    for lib_path in /usr/lib /usr/lib64 /usr/lib/x86_64-linux-gnu /usr/local/lib; do
        if [[ -f "$lib_path/libopenblas.so" || -f "$lib_path/libblas.so" ]]; then
            BLAS_FOUND=true
        fi
        if [[ -f "$lib_path/liblapack.so" ]]; then
            LAPACK_FOUND=true
        fi
    done

    if [ "$BLAS_FOUND" = true ] && [ "$LAPACK_FOUND" = true ]; then
        log_info "BLAS/LAPACK 库已安装" "SysDeps"
        echo -e "${CHECK} BLAS/LAPACK 库已安装"
        return 0
    fi

    log_warn "缺少数学库 - BLAS: $BLAS_FOUND, LAPACK: $LAPACK_FOUND" "SysDeps"
    echo -e "${WARNING} 缺少数学库 - BLAS: $BLAS_FOUND, LAPACK: $LAPACK_FOUND"

    # 确定sudo权限
    local SUDO=""
    if [[ "${CI:-false}" == "true" ]]; then
        SUDO="sudo"
    elif [[ $EUID -eq 0 ]]; then
        SUDO=""
    elif command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        log_error "需要root权限安装系统依赖，但未找到sudo" "SysDeps"
        echo -e "${CROSS} 需要root权限安装系统依赖，但未找到sudo"
        return 1
    fi

    log_info "安装数学库 (BLAS/LAPACK)..." "SysDeps"
    echo -e "${GEAR} 安装数学库 (BLAS/LAPACK)...${NC}"

    case "$OS" in
        ubuntu|debian)
            if log_command "SysDeps" "Install" "$SUDO apt-get install -y --no-install-recommends libopenblas-dev libopenblas0 liblapack-dev libatlas-base-dev"; then
                log_info "数学库安装成功" "SysDeps"
                echo -e "${CHECK} 数学库安装成功"
            else
                log_error "数学库安装失败" "SysDeps"
                echo -e "${CROSS} 数学库安装失败"
                return 1
            fi
            ;;
        centos|rhel)
            if command -v dnf &> /dev/null; then
                log_command "SysDeps" "Install" "$SUDO dnf install -y openblas-devel lapack-devel atlas-devel"
            else
                log_command "SysDeps" "Install" "$SUDO yum install -y openblas-devel lapack-devel atlas-devel"
            fi
            ;;
        fedora)
            log_command "SysDeps" "Install" "$SUDO dnf install -y openblas-devel lapack-devel atlas-devel"
            ;;
        arch|manjaro)
            log_command "SysDeps" "Install" "$SUDO pacman -S --noconfirm openblas lapack atlas-lapack"
            ;;
        *)
            log_warn "未知操作系统: $OS，请手动安装BLAS/LAPACK库" "SysDeps"
            echo -e "${WARNING} 未知操作系统: $OS，请手动安装BLAS/LAPACK库"
            return 1
            ;;
    esac

    return 0
}

# 验证系统依赖安装
verify_system_dependencies() {
    log_info "验证系统依赖..." "SysDeps"
    echo -e "${INFO} 验证系统依赖...${NC}"

    local all_good=true

    # 检查构建工具
    for tool in gcc cmake make pkg-config; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool 未找到" "SysDeps"
            echo -e "${CROSS} $tool 未找到"
            all_good=false
        fi
    done

    # 检查库文件
    local BLAS_FOUND=false
    local LAPACK_FOUND=false

    for lib_path in /usr/lib /usr/lib64 /usr/lib/x86_64-linux-gnu /usr/local/lib; do
        if [[ -f "$lib_path/libopenblas.so" || -f "$lib_path/libblas.so" ]]; then
            BLAS_FOUND=true
        fi
        if [[ -f "$lib_path/liblapack.so" ]]; then
            LAPACK_FOUND=true
        fi
    done

    if [ "$BLAS_FOUND" = false ] || [ "$LAPACK_FOUND" = false ]; then
        log_error "数学库验证失败 - BLAS: $BLAS_FOUND, LAPACK: $LAPACK_FOUND" "SysDeps"
        echo -e "${CROSS} 数学库验证失败 - BLAS: $BLAS_FOUND, LAPACK: $LAPACK_FOUND"
        all_good=false
    fi

    if [ "$all_good" = true ]; then
        log_info "系统依赖验证通过" "SysDeps"
        echo -e "${CHECK} 系统依赖验证通过"
        return 0
    else
        log_error "系统依赖验证失败" "SysDeps"
        echo -e "${WARNING} 系统依赖验证失败"
        return 1
    fi
}

# 主函数：检查和安装所有系统依赖
check_and_install_system_dependencies() {
    echo ""
    echo -e "${BLUE}=== 系统依赖检查和安装 ===${NC}"
    log_info "开始系统依赖检查和安装" "SysDeps"

    # 检测操作系统
    detect_os
    log_info "检测到操作系统: $OS" "SysDeps"
    echo -e "${INFO} 操作系统: $OS"

    # 检查和安装构建工具
    if ! check_and_install_build_tools; then
        log_error "构建工具安装失败" "SysDeps"
        echo -e "${CROSS} 构建工具安装失败"
        return 1
    fi

    # 检查和安装数学库
    if ! check_and_install_math_libraries; then
        log_error "数学库安装失败" "SysDeps"
        echo -e "${CROSS} 数学库安装失败"
        return 1
    fi

    # 验证安装
    if ! verify_system_dependencies; then
        log_warn "系统依赖验证失败，但继续安装" "SysDeps"
        echo -e "${WARNING} 系统依赖验证失败，但继续安装"
    fi

    log_info "系统依赖检查和安装完成" "SysDeps"
    echo -e "${CHECK} 系统依赖检查完成"
    echo ""

    return 0
}
