#!/bin/bash
#
# SAGE Framework 一键闭源发布脚本
# One-click Proprietary Publishing Script for SAGE Framework
#
# 基于 sage-dev-toolkit 的发布功能，自动化所有包的闭源发布流程
# Based on sage-dev-toolkit's publishing functionality, automates proprietary publishing workflow for all packages
#
# 用法 Usage:
#   ./scripts/publish_all_proprietary.sh [options]
#   
# 选项 Options:
#   -h, --help          显示帮助信息 (Show help information)
#   -d, --dry-run       预演模式，不实际发布 (Dry run mode, don't actually publish) 
#   -f, --force         强制发布，跳过确认 (Force publish, skip confirmation)
#   -o, --output DIR    指定输出目录 (Specify output directory)
#   -v, --verbose       详细输出 (Verbose output)
#   -p, --packages LIST 指定要发布的包，用逗号分隔 (Specify packages to publish, comma-separated)
#   --skip-version-check 跳过版本检查 (Skip version check)
#   --parallel          并行发布（实验性功能） (Parallel publishing - experimental)
#
# 示例 Examples:
#   ./scripts/publish_all_proprietary.sh --dry-run
#   ./scripts/publish_all_proprietary.sh --force
#   ./scripts/publish_all_proprietary.sh --packages sage-cli,sage-core
#   ./scripts/publish_all_proprietary.sh --output /tmp/builds --verbose

set -euo pipefail

# ========================================
# 配置和全局变量 Configuration and Globals  
# ========================================

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/packages"

# 默认配置
DRY_RUN=false
FORCE=false
VERBOSE=false
SKIP_VERSION_CHECK=false
PARALLEL=false
OUTPUT_DIR=""
SPECIFIC_PACKAGES=""

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 日志文件
LOG_FILE="$PROJECT_ROOT/publish_all_$(date +%Y%m%d_%H%M%S).log"

# 发布统计
declare -A PUBLISH_RESULTS
TOTAL_PACKAGES=0
SUCCESS_COUNT=0
FAILED_COUNT=0
SKIPPED_COUNT=0

# ========================================
# 工具函数 Utility Functions
# ========================================

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        log "${CYAN}[VERBOSE]${NC} $1"
    fi
}

show_help() {
    cat << EOF
${BOLD}SAGE Framework 一键闭源发布脚本${NC}
One-click Proprietary Publishing Script for SAGE Framework

${BOLD}用法 Usage:${NC}
  $0 [options]

${BOLD}选项 Options:${NC}
  -h, --help              显示帮助信息 (Show help information)
  -d, --dry-run           预演模式，不实际发布 (Dry run mode, don't actually publish)
  -f, --force             强制发布，跳过确认 (Force publish, skip confirmation)
  -o, --output DIR        指定输出目录 (Specify output directory)
  -v, --verbose           详细输出 (Verbose output)
  -p, --packages LIST     指定要发布的包，用逗号分隔 (Specify packages to publish, comma-separated)
      --skip-version-check 跳过版本检查 (Skip version check)
      --parallel          并行发布（实验性功能） (Parallel publishing - experimental)

${BOLD}示例 Examples:${NC}
  $0 --dry-run                                    # 预演模式发布所有包
  $0 --force                                      # 强制发布所有包
  $0 --packages sage-cli,sage-core                # 只发布指定包
  $0 --output /tmp/builds --verbose               # 指定输出目录并启用详细输出

${BOLD}支持的包 Supported Packages:${NC}
EOF
    
    # 显示所有可用的包
    if [ -d "$PACKAGES_DIR" ]; then
        for package in "$PACKAGES_DIR"/*/; do
            if [ -d "$package" ] && [ -f "$package/pyproject.toml" ]; then
                package_name=$(basename "$package")
                echo "  - $package_name"
            fi
        done
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖项..."
    
    # 检查 sage-dev 命令
    if ! command -v sage-dev &> /dev/null; then
        log_error "sage-dev 命令未找到，请确保已安装 sage-dev-toolkit"
        exit 1
    fi
    
    # 检查 Python 环境
    if ! python3 -c "import sage_dev_toolkit" &> /dev/null; then
        log_error "sage_dev_toolkit 模块未找到，请确保已安装"
        exit 1
    fi
    
    # 检查 twine
    if ! command -v twine &> /dev/null; then
        log_warning "twine 未找到，可能无法上传到 PyPI"
    fi
    
    log_success "依赖检查完成"
}

# 获取包列表
get_package_list() {
    local packages=()
    
    if [ -n "$SPECIFIC_PACKAGES" ]; then
        # 解析指定的包列表
        IFS=',' read -ra PKG_ARRAY <<< "$SPECIFIC_PACKAGES"
        for pkg in "${PKG_ARRAY[@]}"; do
            pkg=$(echo "$pkg" | xargs) # 去除空格
            if [ -d "$PACKAGES_DIR/$pkg" ] && [ -f "$PACKAGES_DIR/$pkg/pyproject.toml" ]; then
                packages+=("$pkg")
            else
                log_warning "包 $pkg 不存在或无 pyproject.toml，跳过"
            fi
        done
    else
        # 自动发现所有包
        for package_dir in "$PACKAGES_DIR"/*/; do
            if [ -d "$package_dir" ] && [ -f "$package_dir/pyproject.toml" ]; then
                package_name=$(basename "$package_dir")
                packages+=("$package_name")
            fi
        done
    fi
    
    echo "${packages[@]}"
}

# 获取包信息
get_package_info() {
    local package_path="$1"
    local info_output
    
    info_output=$(sage-dev info "$package_path" 2>/dev/null || echo "Error getting package info")
    echo "$info_output"
}

# 检查包版本
check_package_versions() {
    log_info "检查包版本信息..."
    
    local packages=($1)
    local version_issues=false
    
    for package in "${packages[@]}"; do
        local package_path="$PACKAGES_DIR/$package"
        log_verbose "检查包: $package"
        
        # 获取当前版本
        local current_version
        if command -v python3 &> /dev/null; then
            current_version=$(python3 -c "
import tomli
with open('$package_path/pyproject.toml', 'rb') as f:
    data = tomli.load(f)
print(data.get('project', {}).get('version', 'unknown'))
" 2>/dev/null || echo "unknown")
        else
            current_version="unknown"
        fi
        
        log_info "$package: v$current_version"
        
        # 检查是否已发布（可选功能）
        if [ "$SKIP_VERSION_CHECK" = false ]; then
            # 这里可以添加检查 PyPI 上是否已存在该版本的逻辑
            log_verbose "版本检查功能待实现"
        fi
    done
    
    if [ "$version_issues" = true ] && [ "$FORCE" = false ]; then
        log_error "发现版本问题，使用 --force 跳过检查或修复版本号"
        exit 1
    fi
}

# 发布单个包
publish_package() {
    local package="$1"
    local package_path="$PACKAGES_DIR/$package"
    
    log_info "开始发布包: $package"
    
    # 构建 sage-dev 命令
    local cmd_args=("sage-dev" "proprietary" "$package_path")
    
    if [ "$DRY_RUN" = true ]; then
        cmd_args+=("--dry-run")
    else
        cmd_args+=("--no-dry-run")
    fi
    
    if [ "$FORCE" = true ]; then
        cmd_args+=("--force")
    fi
    
    if [ -n "$OUTPUT_DIR" ]; then
        cmd_args+=("--output" "$OUTPUT_DIR")
    fi
    
    # 执行发布
    local start_time=$(date +%s)
    local result=0
    
    log_verbose "执行命令: ${cmd_args[*]}"
    
    if [ "$VERBOSE" = true ]; then
        "${cmd_args[@]}" 2>&1 | tee -a "$LOG_FILE" || result=$?
    else
        "${cmd_args[@]}" >> "$LOG_FILE" 2>&1 || result=$?
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # 记录结果
    if [ $result -eq 0 ]; then
        if [ "$DRY_RUN" = true ]; then
            PUBLISH_RESULTS["$package"]="SUCCESS (DRY RUN)"
        else
            PUBLISH_RESULTS["$package"]="SUCCESS"
        fi
        ((SUCCESS_COUNT++))
        log_success "$package 发布成功 (耗时: ${duration}s)"
    else
        PUBLISH_RESULTS["$package"]="FAILED"
        ((FAILED_COUNT++))
        log_error "$package 发布失败 (耗时: ${duration}s)"
        
        # 显示最后几行错误日志
        if [ -f "$LOG_FILE" ]; then
            log_error "最后几行错误日志:"
            tail -n 10 "$LOG_FILE" | sed 's/^/  /'
        fi
    fi
    
    return $result
}

# 并行发布包
publish_packages_parallel() {
    local packages=($1)
    local pids=()
    
    log_info "并行发布 ${#packages[@]} 个包..."
    
    # 启动并行作业
    for package in "${packages[@]}"; do
        publish_package "$package" &
        pids+=($!)
        log_verbose "启动并行作业: $package (PID: $!)"
    done
    
    # 等待所有作业完成
    for pid in "${pids[@]}"; do
        if wait "$pid"; then
            log_verbose "并行作业 $pid 完成"
        else
            log_verbose "并行作业 $pid 失败"
        fi
    done
}

# 串行发布包
publish_packages_sequential() {
    local packages=($1)
    
    log_info "串行发布 ${#packages[@]} 个包..."
    
    for package in "${packages[@]}"; do
        publish_package "$package"
        
        # 如果不是预演模式且不是强制模式，询问是否继续
        if [ "$DRY_RUN" = false ] && [ "$FORCE" = false ] && [ "${PUBLISH_RESULTS[$package]}" = "FAILED" ]; then
            echo
            read -p "包 $package 发布失败，是否继续发布其他包？ (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "用户选择停止发布"
                break
            fi
        fi
        
        # 在包之间添加间隔
        if [ "$package" != "${packages[-1]}" ]; then
            log_verbose "等待 2 秒后发布下一个包..."
            sleep 2
        fi
    done
}

# 显示发布摘要
show_summary() {
    log_info "====================================="
    log_info "发布摘要 Publication Summary"
    log_info "====================================="
    log_info "总包数: $TOTAL_PACKAGES"
    log_success "成功: $SUCCESS_COUNT"
    log_error "失败: $FAILED_COUNT"
    
    if [ $SKIPPED_COUNT -gt 0 ]; then
        log_warning "跳过: $SKIPPED_COUNT"
    fi
    
    log_info "详细结果:"
    for package in "${!PUBLISH_RESULTS[@]}"; do
        local status="${PUBLISH_RESULTS[$package]}"
        case $status in
            "SUCCESS")
                log_success "  ✅ $package"
                ;;
            "FAILED")
                log_error "  ❌ $package"
                ;;
            "SKIPPED")
                log_warning "  ⏭️ $package"
                ;;
        esac
    done
    
    log_info "详细日志: $LOG_FILE"
    
    # 如果有失败，显示失败的包
    if [ $FAILED_COUNT -gt 0 ]; then
        log_error "失败的包:"
        for package in "${!PUBLISH_RESULTS[@]}"; do
            if [ "${PUBLISH_RESULTS[$package]}" = "FAILED" ]; then
                log_error "  - $package"
            fi
        done
    fi
}

# 确认发布
confirm_publish() {
    local packages=($1)
    
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    log_info "====================================="
    log_info "发布确认 Publish Confirmation"
    log_info "====================================="
    log_info "将要发布 ${#packages[@]} 个包:"
    
    for package in "${packages[@]}"; do
        echo "  - $package"
    done
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "模式: 预演 (不会实际发布)"
    else
        log_warning "模式: 实际发布到 PyPI"
    fi
    
    echo
    read -p "确认继续？ (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "用户取消发布"
        exit 0
    fi
}

# ========================================
# 主函数 Main Function
# ========================================

main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -p|--packages)
                SPECIFIC_PACKAGES="$2"
                shift 2
                ;;
            --skip-version-check)
                SKIP_VERSION_CHECK=true
                shift
                ;;
            --parallel)
                PARALLEL=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 创建日志文件
    touch "$LOG_FILE"
    
    log_info "====================================="
    log_info "SAGE Framework 闭源包发布开始"
    log_info "开始时间: $(date)"
    log_info "====================================="
    
    # 检查依赖
    check_dependencies
    
    # 获取包列表
    local packages_array=($(get_package_list))
    TOTAL_PACKAGES=${#packages_array[@]}
    
    if [ $TOTAL_PACKAGES -eq 0 ]; then
        log_error "未找到可发布的包"
        exit 1
    fi
    
    # 检查版本
    check_package_versions "${packages_array[*]}"
    
    # 确认发布
    confirm_publish "${packages_array[*]}"
    
    # 开始发布
    local start_time=$(date +%s)
    
    if [ "$PARALLEL" = true ]; then
        log_warning "使用并行发布模式（实验性功能）"
        publish_packages_parallel "${packages_array[*]}"
    else
        publish_packages_sequential "${packages_array[*]}"
    fi
    
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    # 显示摘要
    log_info "====================================="
    log_info "发布完成"
    log_info "结束时间: $(date)"
    log_info "总耗时: ${total_duration}s"
    log_info "====================================="
    
    show_summary
    
    # 返回适当的退出码
    if [ $FAILED_COUNT -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
