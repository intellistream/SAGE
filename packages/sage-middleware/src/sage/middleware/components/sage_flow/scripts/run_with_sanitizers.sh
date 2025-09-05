#!/bin/bash

# SAGE Flow Sanitizer 运行脚本
# 演示如何使用不同的 sanitizer 配置运行程序

set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 显示使用说明
show_usage() {
    echo "SAGE Flow Sanitizer 运行脚本"
    echo ""
    echo "用法: $0 [选项] [可执行文件]"
    echo ""
    echo "选项:"
    echo "  -c, --config CONFIG    使用预定义配置 (dev|prod|test|asan|tsan|msan|ubsan)"
    echo "  -b, --build            重新构建项目"
    echo "  -h, --help             显示此帮助信息"
    echo ""
    echo "预定义配置:"
    echo "  dev    - 开发配置 (Address + Undefined + Leak)"
    echo "  prod   - 生产配置 (Address + Undefined, 最小级别)"
    echo "  test   - 测试配置 (Address + Undefined + Thread, 激进级别)"
    echo "  asan   - 仅 AddressSanitizer"
    echo "  tsan   - 仅 ThreadSanitizer"
    echo "  msan   - 仅 MemorySanitizer (仅 Clang)"
    echo "  ubsan  - 仅 UndefinedBehaviorSanitizer"
    echo ""
    echo "示例:"
    echo "  $0 -c dev ./build/my_program"
    echo "  $0 -b -c test ./build/my_test"
}

# 重新构建项目
rebuild_project() {
    log_info "重新构建项目..."

    local config="$1"
    local build_dir="$PROJECT_ROOT/build_sanitizer_$config"

    mkdir -p "$build_dir"
    cd "$build_dir"

    # 根据配置设置 CMake 选项
    local cmake_options=("-DCMAKE_BUILD_TYPE=Debug")

    case "$config" in
        "dev")
            cmake_options+=("-DSAGE_SANITIZER_ADDRESS=ON")
            cmake_options+=("-DSAGE_SANITIZER_UNDEFINED=ON")
            cmake_options+=("-DSAGE_SANITIZER_LEAK=ON")
            cmake_options+=("-DSAGE_SANITIZER_LEVEL=medium")
            cmake_options+=("-DSAGE_SANITIZER_VERBOSE=ON")
            ;;
        "prod")
            cmake_options+=("-DSAGE_SANITIZER_ADDRESS=ON")
            cmake_options+=("-DSAGE_SANITIZER_UNDEFINED=ON")
            cmake_options+=("-DSAGE_SANITIZER_LEVEL=minimal")
            ;;
        "test")
            cmake_options+=("-DSAGE_SANITIZER_ADDRESS=ON")
            cmake_options+=("-DSAGE_SANITIZER_UNDEFINED=ON")
            cmake_options+=("-DSAGE_SANITIZER_THREAD=ON")
            cmake_options+=("-DSAGE_SANITIZER_LEVEL=aggressive")
            cmake_options+=("-DSAGE_SANITIZER_VERBOSE=ON")
            ;;
        "asan")
            cmake_options+=("-DSAGE_SANITIZER_ADDRESS=ON")
            ;;
        "tsan")
            cmake_options+=("-DSAGE_SANITIZER_THREAD=ON")
            ;;
        "msan")
            cmake_options+=("-DSAGE_SANITIZER_MEMORY=ON")
            ;;
        "ubsan")
            cmake_options+=("-DSAGE_SANITIZER_UNDEFINED=ON")
            ;;
    esac

    log_info "CMake 选项: ${cmake_options[*]}"

    if cmake "${cmake_options[@]}" "$PROJECT_ROOT"; then
        log_success "CMake 配置成功"
    else
        log_error "CMake 配置失败"
        exit 1
    fi

    if make -j$(nproc); then
        log_success "构建成功"
    else
        log_error "构建失败"
        exit 1
    fi

    echo "$build_dir"
}

# 运行程序并设置环境变量
run_with_sanitizer() {
    local executable="$1"
    local config="$2"

    if [[ ! -x "$executable" ]]; then
        log_error "可执行文件不存在或不可执行: $executable"
        exit 1
    fi

    log_info "使用 $config 配置运行: $executable"

    # 设置环境变量
    local env_vars=()

    case "$config" in
        "dev")
            env_vars=(
                "ASAN_OPTIONS=detect_leaks=1:abort_on_error=1:verbosity=1"
                "UBSAN_OPTIONS=abort_on_error=1:verbosity=1:print_stacktrace=1"
                "LSAN_OPTIONS=abort_on_error=1:verbosity=1"
            )
            ;;
        "prod")
            env_vars=(
                "ASAN_OPTIONS=detect_leaks=1:abort_on_error=0"
                "UBSAN_OPTIONS=abort_on_error=0"
            )
            ;;
        "test")
            env_vars=(
                "ASAN_OPTIONS=detect_leaks=1:abort_on_error=1:verbosity=1:debug=1"
                "UBSAN_OPTIONS=abort_on_error=1:verbosity=1:print_stacktrace=1"
                "TSAN_OPTIONS=abort_on_error=1:verbosity=1:history_size=7"
            )
            ;;
        "asan")
            env_vars=(
                "ASAN_OPTIONS=verbosity=1:debug=1:detect_stack_use_after_return=1"
            )
            ;;
        "tsan")
            env_vars=(
                "TSAN_OPTIONS=verbosity=1:history_size=7:detect_deadlocks=1"
            )
            ;;
        "msan")
            env_vars=(
                "MSAN_OPTIONS=verbosity=1"
            )
            ;;
        "ubsan")
            env_vars=(
                "UBSAN_OPTIONS=verbosity=1:print_stacktrace=1"
            )
            ;;
    esac

    # 显示环境变量
    log_info "环境变量设置:"
    for env_var in "${env_vars[@]}"; do
        echo "  export $env_var"
    done

    # 设置环境变量并运行
    log_info "运行程序..."
    (
        for env_var in "${env_vars[@]}"; do
            export "$env_var"
        done
        "$executable"
    )
}

# 主函数
main() {
    local config=""
    local executable=""
    local rebuild=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--config)
                config="$2"
                shift 2
                ;;
            -b|--build)
                rebuild=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                if [[ -z "$executable" ]]; then
                    executable="$1"
                else
                    log_error "未知参数: $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # 验证参数
    if [[ -z "$config" ]]; then
        log_error "必须指定配置类型"
        show_usage
        exit 1
    fi

    if [[ -z "$executable" ]]; then
        log_error "必须指定可执行文件"
        show_usage
        exit 1
    fi

    # 验证配置类型
    case "$config" in
        dev|prod|test|asan|tsan|msan|ubsan)
            ;;
        *)
            log_error "无效的配置类型: $config"
            show_usage
            exit 1
            ;;
    esac

    # 重新构建如果需要
    if [[ "$rebuild" == true ]]; then
        executable=$(rebuild_project "$config")
        executable="$executable/$(basename "$executable")"  # 假设可执行文件在构建目录根目录
    fi

    # 运行程序
    run_with_sanitizer "$executable" "$config"
}

# 执行主函数
main "$@"