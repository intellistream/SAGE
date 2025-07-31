#!/bin/bash
# ===============================================================================
# SAGE Production Wheel Builder
# ===============================================================================
# 功能：将 SAGE 项目打包为生产级 wheel，包含 C++ 扩展且不暴露源码
# 
# 特性：
# - Cython 编译 Python 源码为 .so 文件
# - 构建 C++ 扩展 (sage_db, sage_queue)
# - 删除 Python 源码，仅保留编译后的文件
# - 生成不暴露源码的 wheel 包
#
# 使用方法：
#   ./build_production_wheel.sh
#   ./build_production_wheel.sh --keep-source  # 保留源码
#   ./build_production_wheel.sh --clean-only   # 仅清理
# ===============================================================================

set -e  # 出错时立即退出

# 颜色输出
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
BOLD='\033[1m'
RESET='\033[0m'

# 参数解析
KEEP_SOURCE=false
CLEAN_ONLY=false

for arg in "$@"; do
    case $arg in
        --keep-source)
            KEEP_SOURCE=true
            shift
            ;;
        --clean-only)
            CLEAN_ONLY=true
            shift
            ;;
        --help|-h)
            echo "SAGE Production Wheel Builder"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --keep-source    保留 Python 源码文件"
            echo "  --clean-only     仅执行清理操作"
            echo "  --help, -h       显示此帮助信息"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${RESET}"
            exit 1
            ;;
    esac
done

# 工具函数
print_step() {
    echo -e "\n${BLUE}${BOLD}[STEP]${RESET} ${BLUE}$1${RESET}"
}

print_success() {
    echo -e "${GREEN}${BOLD}[SUCCESS]${RESET} ${GREEN}$1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}${BOLD}[WARNING]${RESET} ${YELLOW}$1${RESET}"
}

print_error() {
    echo -e "${RED}${BOLD}[ERROR]${RESET} ${RED}$1${RESET}"
}

print_info() {
    echo -e "${BOLD}[INFO]${RESET} $1"
}

# 检查依赖
check_dependencies() {
    print_step "检查构建依赖"
    
    # 检查 Python 和必要的包
    if ! python --version | grep -q "3.11"; then
        print_error "需要 Python 3.11"
        exit 1
    fi
    
    # 检查必要的 Python 包
    for pkg in setuptools wheel pybind11 Cython; do
        if ! python -c "import $pkg" 2>/dev/null; then
            print_error "缺少 Python 包: $pkg"
            print_info "请安装: pip install $pkg"
            exit 1
        fi
    done
    
    # 检查 C++ 编译工具
    if ! command -v gcc &> /dev/null; then
        print_error "缺少 GCC 编译器"
        exit 1
    fi
    
    if ! command -v cmake &> /dev/null; then
        print_error "缺少 CMake"
        exit 1
    fi
    
    print_success "所有依赖检查通过"
}

# 清理函数
clean_build() {
    print_step "清理之前的构建"
    
    # 清理构建目录
    rm -rf build dist *.egg-info sage.egg-info sage_ext.egg-info temp_build
    
    # 清理 Python 缓存
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -type f -delete 2>/dev/null || true
    
    # 清理编译产物（除了 sage_ext 下的预构建文件）
    find sage -name "*.so" ! -path "*/mmap_queue/*" -delete 2>/dev/null || true
    
    # 清理临时文件
    rm -f cythonized_files.txt important_init_files.txt
    
    print_success "清理完成"
}

# 设置构建环境
setup_build_environment() {
    print_step "设置构建环境"
    
    # 创建本地临时目录避免磁盘空间问题
    mkdir -p ./temp_build
    
    # 设置环境变量
    export TMPDIR=$(pwd)/temp_build
    export MAX_JOBS=1
    export MAKEFLAGS="-j1"
    
    # 设置编译优化
    export CFLAGS="-O2"
    export CXXFLAGS="-O2"
    
    print_success "构建环境已设置"
    print_info "临时目录: $TMPDIR"
    print_info "并行任务数: $MAX_JOBS"
}

# 构建 C++ 扩展
build_cpp_extensions() {
    print_step "构建 C++ 扩展"
    
    local success_count=0
    local total_count=0
    
    # 构建 sage_queue
    if [ -d "sage_ext/sage_queue" ] && [ -f "sage_ext/sage_queue/build.sh" ]; then
        print_info "构建 sage_queue..."
        total_count=$((total_count + 1))
        if (cd sage_ext/sage_queue && bash build.sh --clean); then
            print_success "✓ sage_queue 构建成功"
            success_count=$((success_count + 1))
        else
            print_warning "✗ sage_queue 构建失败"
        fi
    fi
    
    # 检查 sage_db（可能有编译问题，跳过或修复）
    if [ -d "sage_ext/sage_db" ] && [ -f "sage_ext/sage_db/build.sh" ]; then
        print_info "尝试构建 sage_db..."
        total_count=$((total_count + 1))
        if (cd sage_ext/sage_db && timeout 300 bash build.sh --clean) 2>/dev/null; then
            print_success "✓ sage_db 构建成功"
            success_count=$((success_count + 1))
        else
            print_warning "✗ sage_db 构建失败或超时，将跳过"
        fi
    fi
    
    print_info "C++ 扩展构建完成: $success_count/$total_count"
}

# 构建 Cython 扩展
build_cython_extensions() {
    print_step "构建 Cython 扩展和 Python 绑定"
    
    # 使用受控的环境变量运行构建
    if TMPDIR=$TMPDIR MAX_JOBS=$MAX_JOBS MAKEFLAGS="$MAKEFLAGS" \
       python release_build.py build_ext --inplace; then
        print_success "Cython 扩展构建成功"
    else
        print_error "Cython 扩展构建失败"
        return 1
    fi
    
    # 检查生成的 .so 文件
    local so_count=$(find . -name "*.so" -type f | wc -l)
    print_info "生成了 $so_count 个 .so 文件"
    
    if [ $so_count -eq 0 ]; then
        print_error "没有生成任何 .so 文件"
        return 1
    fi
}

# 清理源码
cleanup_source_files() {
    if [ "$KEEP_SOURCE" = true ]; then
        print_step "保留源码文件（--keep-source 模式）"
        return 0
    fi
    
    print_step "清理 Python 源码文件"
    
    if [ ! -f "cythonized_files.txt" ]; then
        print_warning "cythonized_files.txt 不存在，跳过源码清理"
        return 0
    fi
    
    local total_files=$(wc -l < cythonized_files.txt)
    print_info "准备清理 $total_files 个 Python 源文件"
    
    # 备份重要的 __init__.py 文件
    grep "__init__.py" cythonized_files.txt > important_init_files.txt 2>/dev/null || true
    local init_count=$(wc -l < important_init_files.txt 2>/dev/null || echo 0)
    
    print_info "保留 $init_count 个 __init__.py 文件"
    
    # 删除除了 __init__.py 之外的源文件
    local removed_count=0
    while IFS= read -r file; do
        if [[ "$file" != *"__init__.py" ]] && [ -f "$file" ]; then
            rm "$file"
            removed_count=$((removed_count + 1))
        fi
    done < cythonized_files.txt
    
    print_success "删除了 $removed_count 个 Python 源文件"
    print_info "保留了所有 __init__.py 文件以维持包结构"
}

# 构建 wheel
build_wheel() {
    print_step "构建生产级 wheel 包"
    
    if TMPDIR=$TMPDIR python release_build.py bdist_wheel; then
        print_success "Wheel 包构建成功"
    else
        print_error "Wheel 包构建失败"
        return 1
    fi
}

# 验证 wheel
verify_wheel() {
    print_step "验证 wheel 包"
    
    local wheel_file=$(find dist -name "*.whl" -type f | head -1)
    
    if [ -z "$wheel_file" ]; then
        print_error "未找到 wheel 文件"
        return 1
    fi
    
    print_success "找到 wheel 文件: $(basename "$wheel_file")"
    
    # 显示文件大小
    local size=$(ls -lh "$wheel_file" | awk '{print $5}')
    print_info "文件大小: $size"
    
    # 检查内容
    local so_count=$(unzip -l "$wheel_file" | grep -c "\.so$" || echo 0)
    local py_count=$(unzip -l "$wheel_file" | grep -c "\.py$" || echo 0)
    
    print_info "包含 $so_count 个 .so 文件（编译后的代码）"
    print_info "包含 $py_count 个 .py 文件（主要是 __init__.py）"
    
    # 检查关键扩展
    print_info "检查关键扩展模块:"
    unzip -l "$wheel_file" | grep -E "(sage_db|sage_queue|_sage)" | head -5 | while read line; do
        echo "  $line"
    done
    
    print_success "Wheel 包验证完成"
    echo ""
    echo -e "${GREEN}${BOLD}🎉 生产级 wheel 包构建成功！${RESET}"
    echo -e "${BOLD}文件位置:${RESET} $wheel_file"
    echo -e "${BOLD}安装命令:${RESET} pip install $wheel_file"
}

# 主函数
main() {
    echo -e "${BLUE}${BOLD}"
    echo "==============================================================================="
    echo "                        SAGE Production Wheel Builder"
    echo "==============================================================================="
    echo -e "${RESET}"
    echo "目标: 构建不暴露源码的生产级 wheel 包"
    echo "包含: Cython 编译 + C++ 扩展 + 源码清理"
    echo ""
    
    # 如果只是清理
    if [ "$CLEAN_ONLY" = true ]; then
        clean_build
        print_success "清理完成"
        exit 0
    fi
    
    # 检查当前目录
    if [ ! -f "release_build.py" ]; then
        print_error "请在 SAGE 项目根目录运行此脚本"
        exit 1
    fi
    
    # 执行构建流程
    check_dependencies
    clean_build
    setup_build_environment
    build_cpp_extensions
    build_cython_extensions
    cleanup_source_files
    build_wheel
    verify_wheel
    
    echo ""
    echo -e "${GREEN}${BOLD}🚀 构建流程全部完成！${RESET}"
    echo ""
    echo -e "${BOLD}下一步操作:${RESET}"
    echo "1. 测试安装: pip install dist/*.whl"
    echo "2. 验证功能: python -c 'import sage; print(sage.__version__)'"
    echo "3. 分发使用: 将 wheel 文件分发给用户"
    echo ""
}

# 错误处理
trap 'print_error "构建过程中发生错误，请检查上面的输出"; exit 1' ERR

# 运行主函数
main "$@"
