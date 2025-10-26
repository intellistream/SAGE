#!/bin/bash
# SAGE System Dependencies Installer
# 安装 SAGE C++ 扩展所需的系统依赖

set -e

echo "🔧 SAGE 系统依赖安装器"
echo "=================================="

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

# 安装基础构建工具
install_build_tools() {
    echo "📦 安装基础构建工具..."

    case "$OS" in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y --no-install-recommends \
                build-essential \
                cmake \
                pkg-config
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                dnf groupinstall -y "Development Tools"
                dnf install -y cmake pkg-config
            else
                yum groupinstall -y "Development Tools"
                yum install -y cmake pkgconfig
            fi
            ;;
        arch|manjaro)
            pacman -S --noconfirm base-devel cmake pkgconf
            ;;
        *)
            echo "⚠️  未知操作系统: $OS，请手动安装构建工具"
            return 1
            ;;
    esac

    echo "✅ 基础构建工具安装完成"
}

# 安装数学库 (BLAS/LAPACK)
install_math_libraries() {
    echo "📦 安装数学库 (BLAS/LAPACK)..."

    case "$OS" in
        ubuntu|debian)
            apt-get install -y --no-install-recommends \
                libopenblas-dev \
                libopenblas0 \
                liblapack-dev \
                libatlas-base-dev
            ;;
        centos|rhel)
            if command -v dnf &> /dev/null; then
                dnf install -y openblas-devel lapack-devel atlas-devel
            else
                yum install -y openblas-devel lapack-devel atlas-devel
            fi
            ;;
        fedora)
            dnf install -y openblas-devel lapack-devel atlas-devel
            ;;
        arch|manjaro)
            pacman -S --noconfirm openblas lapack atlas-lapack
            ;;
        *)
            echo "⚠️  未知操作系统: $OS，尝试通过包管理器安装BLAS/LAPACK"
            return 1
            ;;
    esac

    echo "✅ 数学库安装完成"
}

# 验证安装
verify_installation() {
    echo "🔍 验证安装..."

    # 检查构建工具
    if ! command -v gcc &> /dev/null; then
        echo "❌ gcc 未找到"
        return 1
    fi

    if ! command -v cmake &> /dev/null; then
        echo "❌ cmake 未找到"
        return 1
    fi

    echo "✅ 构建工具验证通过"

    # 检查库文件
    echo "🔍 检查 BLAS/LAPACK 库..."

    # 尝试找到库文件
    BLAS_FOUND=false
    LAPACK_FOUND=false

    for lib_path in /usr/lib /usr/lib64 /usr/lib/x86_64-linux-gnu /usr/local/lib; do
        if [[ -f "$lib_path/libopenblas.so" || -f "$lib_path/libblas.so" ]]; then
            BLAS_FOUND=true
            echo "✅ 找到 BLAS 库: $lib_path"
            break
        fi
    done

    for lib_path in /usr/lib /usr/lib64 /usr/lib/x86_64-linux-gnu /usr/local/lib; do
        if [[ -f "$lib_path/liblapack.so" ]]; then
            LAPACK_FOUND=true
            echo "✅ 找到 LAPACK 库: $lib_path"
            break
        fi
    done

    if [[ "$BLAS_FOUND" == true && "$LAPACK_FOUND" == true ]]; then
        echo "✅ 数学库验证通过"
        return 0
    else
        echo "⚠️  部分数学库未找到，但可能仍可正常构建"
        return 0
    fi
}

# 主函数
main() {
    echo "🔍 检测操作系统..."
    detect_os
    echo "📋 操作系统: $OS"

    # 检查权限和环境
    if [[ "${CI:-false}" == "true" ]]; then
        echo "🤖 CI 环境检测到，使用 sudo 安装依赖"
        SUDO="sudo"
    elif [[ $EUID -eq 0 ]]; then
        echo "🔐 以 root 用户运行"
        SUDO=""
    elif command -v sudo &> /dev/null; then
        echo "🔐 使用 sudo 安装依赖"
        SUDO="sudo"
    else
        echo "❌ 需要 root 权限或 sudo 来安装系统包"
        echo "请以 root 用户运行或安装 sudo"
        exit 1
    fi

    # 安装依赖
    if [[ -n "$SUDO" ]]; then
        echo "📝 将使用 sudo 安装系统包..."
        $SUDO bash -c "$(declare -f install_build_tools); install_build_tools"
        $SUDO bash -c "$(declare -f install_math_libraries); install_math_libraries"
    else
        install_build_tools
        install_math_libraries
    fi

    # 验证安装
    verify_installation

    echo ""
    echo "🎉 系统依赖安装完成！"
    echo "现在可以运行 'sage extensions install all' 来构建 C++ 扩展"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "使用方法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --help, -h     显示此帮助信息"
            echo "  --verify-only  只验证安装，不安装新包"
            echo ""
            echo "此脚本会安装 SAGE C++ 扩展所需的系统依赖，包括："
            echo "  - 构建工具 (gcc, cmake, make)"
            echo "  - 数学库 (BLAS, LAPACK)"
            exit 0
            ;;
        --verify-only)
            detect_os
            verify_installation
            exit $?
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看可用选项"
            exit 1
            ;;
    esac
done

# 运行主函数
main "$@"
