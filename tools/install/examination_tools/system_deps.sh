#!/bin/bash
# SAGE 系统依赖管理模块
# 集成到quickstart.sh架构中的系统依赖检查和安装

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

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
    local log_file="${1:-install.log}"
    echo -e "${INFO} 检查基础构建工具..."

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

    if [ ${#missing_tools[@]} -eq 0 ]; then
        echo -e "${CHECK} 基础构建工具已安装"
        return 0
    fi

    echo -e "${WARNING} 缺少构建工具: ${missing_tools[*]}"
    echo "$(date): 缺少构建工具: ${missing_tools[*]}" >> "$log_file"

    # 确定sudo权限
    local SUDO=""
    if [[ "${CI:-false}" == "true" ]]; then
        SUDO="sudo"
    elif [[ $EUID -eq 0 ]]; then
        SUDO=""
    elif command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        echo -e "${CROSS} 需要root权限安装系统依赖，但未找到sudo"
        return 1
    fi

    echo -e "${GEAR} 安装基础构建工具..."

    case "$OS" in
        ubuntu|debian)
            $SUDO apt-get update -qq >> "$log_file" 2>&1
            if $SUDO apt-get install -y --no-install-recommends \
                build-essential \
                cmake \
                pkg-config >> "$log_file" 2>&1; then
                echo -e "${CHECK} 构建工具安装成功"
                echo "$(date): 构建工具安装成功" >> "$log_file"
            else
                echo -e "${CROSS} 构建工具安装失败"
                echo "$(date): 构建工具安装失败" >> "$log_file"
                return 1
            fi
            ;;
        centos|rhel)
            if command -v dnf &> /dev/null; then
                $SUDO dnf groupinstall -y "Development Tools" >> "$log_file" 2>&1
                $SUDO dnf install -y cmake pkg-config >> "$log_file" 2>&1
            else
                $SUDO yum groupinstall -y "Development Tools" >> "$log_file" 2>&1
                $SUDO yum install -y cmake pkg-config >> "$log_file" 2>&1
            fi
            ;;
        fedora)
            $SUDO dnf groupinstall -y "Development Tools" >> "$log_file" 2>&1
            $SUDO dnf install -y cmake pkg-config >> "$log_file" 2>&1
            ;;
        arch|manjaro)
            $SUDO pacman -S --noconfirm base-devel cmake pkg-config >> "$log_file" 2>&1
            ;;
        *)
            echo -e "${WARNING} 未知操作系统: $OS，请手动安装构建工具"
            return 1
            ;;
    esac

    return 0
}

# 检查并安装数学库 (BLAS/LAPACK)
check_and_install_math_libraries() {
    local log_file="${1:-install.log}"
    echo -e "${INFO} 检查数学库 (BLAS/LAPACK)..."

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
        echo -e "${CHECK} BLAS/LAPACK 库已安装"
        return 0
    fi

    echo -e "${WARNING} 缺少数学库 - BLAS: $BLAS_FOUND, LAPACK: $LAPACK_FOUND"
    echo "$(date): 缺少数学库 - BLAS: $BLAS_FOUND, LAPACK: $LAPACK_FOUND" >> "$log_file"

    # 确定sudo权限
    local SUDO=""
    if [[ "${CI:-false}" == "true" ]]; then
        SUDO="sudo"
    elif [[ $EUID -eq 0 ]]; then
        SUDO=""
    elif command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        echo -e "${CROSS} 需要root权限安装系统依赖，但未找到sudo"
        return 1
    fi

    echo -e "${GEAR} 安装数学库 (BLAS/LAPACK)..."

    case "$OS" in
        ubuntu|debian)
            if $SUDO apt-get install -y --no-install-recommends \
                libopenblas-dev \
                libopenblas0 \
                liblapack-dev \
                libatlas-base-dev >> "$log_file" 2>&1; then
                echo -e "${CHECK} 数学库安装成功"
                echo "$(date): 数学库安装成功" >> "$log_file"
            else
                echo -e "${CROSS} 数学库安装失败"
                echo "$(date): 数学库安装失败" >> "$log_file"
                return 1
            fi
            ;;
        centos|rhel)
            if command -v dnf &> /dev/null; then
                $SUDO dnf install -y openblas-devel lapack-devel atlas-devel >> "$log_file" 2>&1
            else
                $SUDO yum install -y openblas-devel lapack-devel atlas-devel >> "$log_file" 2>&1
            fi
            ;;
        fedora)
            $SUDO dnf install -y openblas-devel lapack-devel atlas-devel >> "$log_file" 2>&1
            ;;
        arch|manjaro)
            $SUDO pacman -S --noconfirm openblas lapack atlas-lapack >> "$log_file" 2>&1
            ;;
        *)
            echo -e "${WARNING} 未知操作系统: $OS，请手动安装BLAS/LAPACK库"
            return 1
            ;;
    esac

    return 0
}

# 验证系统依赖安装
verify_system_dependencies() {
    local log_file="${1:-install.log}"
    echo -e "${INFO} 验证系统依赖..."

    local all_good=true

    # 检查构建工具
    for tool in gcc cmake make pkg-config; do
        if ! command -v "$tool" &> /dev/null; then
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
        echo -e "${CROSS} 数学库验证失败 - BLAS: $BLAS_FOUND, LAPACK: $LAPACK_FOUND"
        all_good=false
    fi

    if [ "$all_good" = true ]; then
        echo -e "${CHECK} 系统依赖验证通过"
        echo "$(date): 系统依赖验证通过" >> "$log_file"
        return 0
    else
        echo -e "${WARNING} 系统依赖验证失败"
        echo "$(date): 系统依赖验证失败" >> "$log_file"
        return 1
    fi
}

# 主函数：检查和安装所有系统依赖
check_and_install_system_dependencies() {
    local log_file="${1:-install.log}"

    echo ""
    echo -e "${BLUE}=== 系统依赖检查和安装 ===${NC}"
    echo "$(date): 开始系统依赖检查和安装" >> "$log_file"

    # 检测操作系统
    detect_os
    echo -e "${INFO} 操作系统: $OS"
    echo "$(date): 检测到操作系统: $OS" >> "$log_file"

    # 检查和安装构建工具
    if ! check_and_install_build_tools "$log_file"; then
        echo -e "${CROSS} 构建工具安装失败"
        return 1
    fi

    # 检查和安装数学库
    if ! check_and_install_math_libraries "$log_file"; then
        echo -e "${CROSS} 数学库安装失败"
        return 1
    fi

    # 验证安装
    if ! verify_system_dependencies "$log_file"; then
        echo -e "${WARNING} 系统依赖验证失败，但继续安装"
        echo "$(date): 系统依赖验证失败，但继续安装" >> "$log_file"
    fi

    echo "$(date): 系统依赖检查和安装完成" >> "$log_file"
    echo -e "${CHECK} 系统依赖检查完成"
    echo ""

    return 0
}
