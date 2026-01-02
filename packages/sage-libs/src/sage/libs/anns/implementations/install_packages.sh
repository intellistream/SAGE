#!/bin/bash
# ============================================================================
# 安装脚本：安装所有已构建的算法 Python 包
# ============================================================================
#
# 本脚本用于安装 algorithms_impl 文件夹中所有已构建的 Python 包
#
# 前置条件：
#   - 已经运行过 build_all.sh 构建所有算法
#
# 使用方法:
#   ./install_packages.sh [--force]
#
# 选项:
#   --force    强制重新安装（即使已安装）
#   --help     显示帮助信息
# ============================================================================

set -e  # 遇到错误立即退出

# ============================================================================
# 颜色定义
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# 辅助函数
# ============================================================================
print_header() {
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# ============================================================================
# 解析命令行参数
# ============================================================================
FORCE_REINSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_REINSTALL=true
            shift
            ;;
        --help)
            head -n 17 "$0" | tail -n +2 | sed 's/^# //'
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================================================
# 环境检查
# ============================================================================
print_header "Installation Check"

# 获取脚本所在目录 (algorithms_impl/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_info "Working directory: $SCRIPT_DIR"

# 检查 Python 和 pip
if ! command -v python3 &> /dev/null; then
    print_error "python3 not found. Please install Python 3."
    exit 1
fi

if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    print_error "pip not found. Please install pip."
    exit 1
fi

PIP_CMD=$(command -v pip3 2>/dev/null || command -v pip)
print_success "Python: $(python3 --version)"
print_success "pip: $($PIP_CMD --version)"

# ============================================================================
# 安装 PyCANDY
# ============================================================================
print_header "Installing PyCANDY"

SO_FILE=$(ls PyCANDYAlgo*.so 2>/dev/null | head -1)
if [ -n "$SO_FILE" ] && [ -f "setup.py" ]; then
    print_info "Found PyCANDYAlgo: $SO_FILE"

    if [ "$FORCE_REINSTALL" = true ]; then
        print_info "Force reinstalling PyCANDYAlgo..."
        $PIP_CMD install -e . --no-build-isolation --force-reinstall
    else
        print_info "Installing PyCANDYAlgo..."
        $PIP_CMD install -e . --no-build-isolation
    fi

    # 验证安装
    if python3 -c "import PyCANDYAlgo" 2>/dev/null; then
        print_success "PyCANDYAlgo installed and verified"
    else
        print_error "PyCANDYAlgo installation verification failed"
        exit 1
    fi
else
    print_warning "PyCANDYAlgo not found. Please run build_all.sh first."
fi

# ============================================================================
# 安装 VSAG
# ============================================================================
print_header "Installing VSAG"

if [ -d "vsag/wheelhouse" ]; then
    WHEEL_FILE=$(ls vsag/wheelhouse/pyvsag*.whl 2>/dev/null | head -1)

    if [ -n "$WHEEL_FILE" ]; then
        print_info "Found VSAG wheel: $WHEEL_FILE"

        if [ "$FORCE_REINSTALL" = true ]; then
            print_info "Force reinstalling pyvsag..."
            $PIP_CMD install "$WHEEL_FILE" --force-reinstall
        else
            print_info "Installing pyvsag..."
            $PIP_CMD install "$WHEEL_FILE"
        fi

        # 验证安装
        if python3 -c "import pyvsag" 2>/dev/null; then
            print_success "pyvsag installed and verified"
        else
            print_error "pyvsag installation verification failed"
            exit 1
        fi
    else
        print_warning "VSAG wheel not found. Please run build_all.sh first."
    fi
else
    print_warning "VSAG wheelhouse directory not found. Please run build_all.sh first."
fi

# ============================================================================
# 安装总结
# ============================================================================
print_header "Installation Summary"

echo "Installed packages:"
python3 -c "
import sys
packages = ['PyCANDYAlgo', 'pyvsag']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'  ✓ {pkg}')
    except ImportError:
        print(f'  ✗ {pkg} (not installed)')
"

echo ""
print_success "Installation completed!"
echo ""
print_info "You can verify the installation with:"
echo "  python3 -c 'import PyCANDYAlgo; import pyvsag'"
