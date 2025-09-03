#!/bin/bash
#
# SAGE Framework 快速测试脚本
# Quick Test Script for SAGE Framework
#
# 快速测试主要包，适用于日常开发验证
# Quick test for main packages, suitable for daily development verification

set -euo pipefail

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 引入工具模块
source "$PROJECT_ROOT/scripts/logging.sh" 2>/dev/null || {
    # 基础日志函数（如果logging.sh不可用）
    log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
    log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
    log_warning() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
    log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }
}

# 快速测试配置
QUICK_PACKAGES=("sage-common" "sage-kernel" "sage-libs" "sage-middleware")
QUICK_TIMEOUT=120
QUICK_JOBS=3

show_help() {
    cat << EOF
SAGE Framework 快速测试工具

用法: $0 [选项]

选项:
  -v, --verbose       详细输出模式
  -s, --summary       只显示摘要结果
  -h, --help          显示此帮助信息

特性:
  🎯 只测试有测试的主要包 (${QUICK_PACKAGES[*]})
  🚀 自动并行执行 ($QUICK_JOBS 个worker)
  ⚡ 较短的超时时间 ($QUICK_TIMEOUT 秒)
  🛡️ 自动继续执行，即使某个包失败

EOF
}

# 解析参数
VERBOSE=false
SUMMARY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--summary)
            SUMMARY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 构建参数
ARGS=(
    "--jobs" "$QUICK_JOBS"
    "--timeout" "$QUICK_TIMEOUT"
    "--continue-on-error"
)

if [[ $VERBOSE == true ]]; then
    ARGS+=("--verbose")
fi

if [[ $SUMMARY == true ]]; then
    ARGS+=("--summary")
fi

# 添加要测试的包
ARGS+=("${QUICK_PACKAGES[@]}")

# 调用主测试脚本
log_info "🚀 启动 SAGE Framework 快速测试"
log_info "测试包: ${QUICK_PACKAGES[*]}"
echo ""

exec "$SCRIPT_DIR/test_all_packages.sh" "${ARGS[@]}"
