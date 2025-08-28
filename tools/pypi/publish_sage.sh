#!/bin/bash
#
# SAGE Framework PyPI 发布脚本
# SAGE Framework PyPI Publishing Script
#
# 用于发布新重构的 SAGE 包到 PyPI
# For publishing the new restructured SAGE packages to PyPI

set -uo pipefail

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 颜色配置
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "${BOLD}${BLUE}$1${NC}"
}

# 检查依赖
check_dependencies() {
    log_header "🔍 检查依赖"
    
    if ! command -v twine &> /dev/null; then
        log_error "twine 未安装，请先安装: pip install twine"
        exit 1
    fi
    
    if ! command -v python &> /dev/null; then
        log_error "Python 未安装"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

# 清理旧的构建文件
clean_build_artifacts() {
    log_header "🧹 清理构建产物"
    
    if [[ -f "$PROJECT_ROOT/cleanup_build_artifacts.py" ]]; then
        cd "$PROJECT_ROOT"
        python cleanup_build_artifacts.py
    else
        # 手动清理
        find "$PROJECT_ROOT/packages" -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true
        find "$PROJECT_ROOT/packages" -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
        find "$PROJECT_ROOT/packages" -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
    fi
    
    log_success "构建产物清理完成"
}

# 构建单个包
build_package() {
    local package_path="$1"
    local package_name=$(basename "$package_path")
    
    log_info "构建包: $package_name"
    
    cd "$package_path"
    
    # 检查 pyproject.toml 是否存在
    if [[ ! -f "pyproject.toml" ]]; then
        log_error "$package_name: 缺少 pyproject.toml"
        return 1
    fi
    
    # 构建包
    if ! python -m build --wheel; then
        log_error "$package_name: 构建失败"
        return 1
    fi
    
    log_success "$package_name: 构建完成"
    return 0
}

# 上传单个包
upload_package() {
    local package_path="$1"
    local package_name=$(basename "$package_path")
    local dry_run="$2"
    
    log_info "上传包: $package_name"
    
    cd "$package_path"
    
    if [[ ! -d "dist" ]]; then
        log_error "$package_name: 缺少 dist 目录"
        return 1
    fi
    
    # 构建上传命令
    local upload_cmd="twine upload dist/*"
    
    if [[ "$dry_run" == "true" ]]; then
        upload_cmd="$upload_cmd --repository testpypi"
        log_info "$package_name: 上传到 TestPyPI (预演模式)"
    else
        log_info "$package_name: 上传到 PyPI"
    fi
    
    # 执行上传
    local upload_output
    upload_output=$(eval "$upload_cmd" 2>&1)
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "$package_name: 上传成功"
        return 0
    else
        # 检查是否为文件已存在错误
        if echo "$upload_output" | grep -q "File already exists\|already exists\|400 Bad Request"; then
            log_warning "$package_name: 文件已存在，跳过"
            return 0
        else
            log_error "$package_name: 上传失败 (退出码: $exit_code)"
            log_error "错误信息: $upload_output"
            return 1
        fi
    fi
}

# 主发布流程
publish_packages() {
    local dry_run="$1"
    local packages=("$@")
    
    if [[ "$dry_run" == "true" ]]; then
        log_header "🚀 SAGE 包发布 (TestPyPI 预演模式)"
    else
        log_header "🚀 SAGE 包发布 (PyPI 正式发布)"
    fi
    
    # 定义发布顺序 - 按依赖关系排序
    local publish_order=(
        "sage-common"      # 基础工具包，其他包可能依赖
        "sage-kernel"      # 内核
        "sage-middleware"  # 中间件
        "sage-libs"        # 应用
        "sage"            # Meta 包，依赖所有其他包
    )
    
    local success_count=0
    local failed_count=0
    local skipped_count=0
    
    for package in "${publish_order[@]}"; do
        local package_path="$PROJECT_ROOT/packages/$package"
        
        if [[ ! -d "$package_path" ]]; then
            log_warning "$package: 目录不存在，跳过"
            ((skipped_count++))
            continue
        fi
        
        echo
        log_header "📦 处理包: $package"
        
        # 构建包
        if ! build_package "$package_path"; then
            log_error "$package: 构建失败"
            ((failed_count++))
            continue
        fi
        
        # 上传包
        if upload_package "$package_path" "$dry_run"; then
            ((success_count++))
        else
            ((failed_count++))
        fi
    done
    
    # 显示摘要
    echo
    log_header "📊 发布摘要"
    log_success "成功: $success_count"
    log_warning "跳过: $skipped_count"
    log_error "失败: $failed_count"
    echo "总计: $((success_count + skipped_count + failed_count))"
    
    if [[ $failed_count -eq 0 ]]; then
        echo
        log_success "🎉 所有包发布完成！"
        return 0
    else
        echo
        log_error "💥 有 $failed_count 个包发布失败"
        return 1
    fi
}

# 显示帮助信息
show_help() {
    echo "SAGE Framework PyPI 发布工具"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  --dry-run    预演模式，上传到 TestPyPI"
    echo "  --clean      仅清理构建产物，不发布"
    echo "  --help       显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0                # 发布到 PyPI"
    echo "  $0 --dry-run      # 预演模式，发布到 TestPyPI"
    echo "  $0 --clean        # 仅清理构建产物"
}

# 主函数
main() {
    local dry_run="false"
    local clean_only="false"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run="true"
                shift
                ;;
            --clean)
                clean_only="true"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                echo
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查依赖
    check_dependencies
    
    # 清理构建产物
    clean_build_artifacts
    
    if [[ "$clean_only" == "true" ]]; then
        log_success "仅清理模式完成"
        exit 0
    fi
    
    # 发布包
    publish_packages "$dry_run"
}

# 执行主函数
main "$@"
