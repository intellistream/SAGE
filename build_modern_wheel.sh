#!/bin/bash
# =============================================================================== 
# SAGE 现代化 Wheel 构建脚本
# ===============================================================================
# 基于 pyproject.toml 的现代化构建流程
# 支持纯 Python 和包含 C++ 扩展的构建
# ===============================================================================

set -e

# 颜色定义
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
BOLD='\033[1m'
RESET='\033[0m'

# 工具函数
print_step() {
    echo -e "\n${BLUE}${BOLD}[STEP]${RESET} ${BLUE}$1${RESET}"
}

print_success() {
    echo -e "${GREEN}✅ $1${RESET}"
}

print_error() {
    echo -e "${RED}❌ $1${RESET}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${RESET}"
}

# 参数解析
BUILD_CPP=false
CLEAN_ONLY=false

for arg in "$@"; do
    case $arg in
        --with-cpp)
            BUILD_CPP=true
            shift
            ;;
        --clean-only)
            CLEAN_ONLY=true
            shift
            ;;
        --help|-h)
            echo "SAGE 现代化 Wheel 构建脚本"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --with-cpp       包含 C++ 扩展"
            echo "  --clean-only     仅执行清理"
            echo "  --help, -h       显示帮助"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${RESET}"
            exit 1
            ;;
    esac
done

# 检查依赖
check_dependencies() {
    print_step "检查构建依赖"
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未找到"
        exit 1
    fi
    
    # 检查 Python 版本
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version < 3.11" | bc -l) -eq 1 ]]; then
        print_error "需要 Python 3.11 或更高版本，当前版本: $python_version"
        exit 1
    fi
    print_success "Python $python_version ✓"
    
    # 检查 pip
    if ! python3 -m pip --version &> /dev/null; then
        print_error "pip 未找到"
        exit 1
    fi
    print_success "pip ✓"
    
    # 检查构建工具
    if ! python3 -c "import build" 2>/dev/null; then
        print_info "安装 build..."
        python3 -m pip install build
    fi
    print_success "build ✓"
    
    if [ "$BUILD_CPP" = true ]; then
        if ! command -v gcc &> /dev/null; then
            print_warning "gcc 未找到，C++ 扩展可能无法构建"
        else
            print_success "gcc ✓"
        fi
        
        if ! command -v cmake &> /dev/null; then
            print_warning "cmake 未找到，C++ 扩展可能无法构建"
        else
            print_success "cmake ✓"
        fi
    fi
}

# 清理构建文件
clean_build() {
    print_step "清理构建文件"
    
    # 删除构建目录
    rm -rf build dist *.egg-info .eggs
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    
    print_success "清理完成"
}

# 构建 C++ 扩展
build_cpp_extensions() {
    if [ "$BUILD_CPP" != true ]; then
        print_info "跳过 C++ 扩展构建"
        return 0
    fi
    
    print_step "构建 C++ 扩展"
    
    # 构建 sage_queue
    if [ -d "sage_ext/sage_queue" ]; then
        print_info "构建 sage_queue..."
        if [ -f "sage_ext/sage_queue/build.sh" ]; then
            (cd sage_ext/sage_queue && bash build.sh) || print_warning "sage_queue 构建失败"
        else
            print_warning "未找到 sage_queue 构建脚本"
        fi
    fi
    
    # 构建 sage_db
    if [ -d "sage_ext/sage_db" ]; then
        print_info "构建 sage_db..."
        if [ -f "sage_ext/sage_db/build.sh" ]; then
            (cd sage_ext/sage_db && bash build.sh) || print_warning "sage_db 构建失败"
        else
            print_warning "未找到 sage_db 构建脚本"
        fi
    fi
    
    print_success "C++ 扩展构建完成"
}

# 构建 wheel
build_wheel() {
    print_step "构建 wheel 包"
    
    # 检查是否有 pyproject.toml
    if [ ! -f "pyproject.toml" ]; then
        print_error "未找到 pyproject.toml，请先创建该文件"
        exit 1
    fi
    
    # 设置构建环境变量
    export SAGE_BUILD_CPP=$BUILD_CPP
    
    if [ "$BUILD_CPP" = true ]; then
        print_info "构建包含 C++ 扩展的 wheel..."
        python3 -m build
    else
        print_info "构建纯 Python wheel..."
        python3 -m build --wheel
    fi
    
    print_success "Wheel 构建完成"
}

# 验证 wheel
verify_wheel() {
    print_step "验证 wheel 包"
    
    wheel_file=$(find dist -name "*.whl" -type f | head -1)
    
    if [ -z "$wheel_file" ]; then
        print_error "未找到 wheel 文件"
        return 1
    fi
    
    print_success "找到 wheel: $(basename "$wheel_file")"
    
    # 显示文件大小
    size=$(ls -lh "$wheel_file" | awk '{print $5}')
    print_info "文件大小: $size"
    
    # 检查内容
    print_info "检查包内容:"
    if command -v unzip &> /dev/null; then
        py_count=$(unzip -l "$wheel_file" | grep -c "\.py$" || echo 0)
        so_count=$(unzip -l "$wheel_file" | grep -c "\.so$" || echo 0)
        print_info "  Python 文件: $py_count 个"
        print_info "  编译库文件: $so_count 个"
    fi
    
    print_success "验证完成"
    
    echo ""
    echo -e "${GREEN}${BOLD}🎉 Wheel 包构建成功！${RESET}"
    echo -e "${BOLD}文件位置:${RESET} $wheel_file"
    echo -e "${BOLD}安装命令:${RESET} pip install $wheel_file"
}

# 主函数
main() {
    echo -e "${BLUE}${BOLD}"
    echo "==============================================================================="
    echo "                    SAGE 现代化 Wheel 构建脚本"
    echo "==============================================================================="
    echo -e "${RESET}"
    echo "基于 pyproject.toml 的现代化构建流程"
    if [ "$BUILD_CPP" = true ]; then
        echo "模式: 包含 C++ 扩展"
    else
        echo "模式: 纯 Python"
    fi
    echo ""
    
    # 检查项目根目录
    if [ ! -f "pyproject.toml" ]; then
        print_error "请在包含 pyproject.toml 的项目根目录运行此脚本"
        exit 1
    fi
    
    # 仅清理模式
    if [ "$CLEAN_ONLY" = true ]; then
        clean_build
        print_success "清理完成"
        exit 0
    fi
    
    # 执行构建流程
    check_dependencies
    clean_build
    build_cpp_extensions
    build_wheel
    verify_wheel
    
    echo ""
    echo -e "${GREEN}${BOLD}🚀 构建流程完成！${RESET}"
    echo ""
    echo -e "${BOLD}下一步操作:${RESET}"
    echo "1. 测试安装: pip install dist/*.whl"
    echo "2. 验证导入: python -c 'import sage; print(sage.__version__)'"
    echo "3. 上传到 PyPI: twine upload dist/*.whl"
}

# 错误处理
trap 'print_error "构建过程中发生错误"; exit 1' ERR

# 运行主函数
main "$@"
