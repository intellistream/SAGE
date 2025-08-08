#!/bin/bash
#
# 一键闭源打包发布脚本
# One-click Closed-source Packaging and Publishing Script
#
# 基于 sage-dev-toolkit 的 publish.py 功能，自动化闭源包的编译、打包和发布流程
# Based on sage-dev-toolkit's publish.py functionality, automates the compilation, packaging, and publishing workflow for proprietary packages
#
# 用法 Usage:
#   ./scripts/proprietary_publish.sh [options] [package_names...]
#   
# 选项 Options:
#   -h, --help          显示帮助信息 (Show help information)
#   -d, --dry-run       预演模式，不实际发布 (Dry run mode, don't actually publish)
#   -f, --force         强制发布，跳过确认 (Force publish, skip confirmation)
#   -o, --output DIR    指定输出目录 (Specify output directory)
#   -t, --test-pypi     发布到测试PyPI (Publish to Test PyPI)
#   -a, --all           发布所有包 (Publish all packages)
#   -v, --verbose       详细输出 (Verbose output)
#   -c, --clean         清理构建缓存 (Clean build cache)
#   --no-compile        跳过编译步骤（仅打包） (Skip compilation step, package only)
#   --no-upload         只编译打包，不上传 (Only compile and package, don't upload)
#
# 示例 Examples:
#   ./scripts/proprietary_publish.sh --dry-run --all
#   ./scripts/proprietary_publish.sh --force sage-kernel sage-middleware
#   ./scripts/proprietary_publish.sh --output /tmp/builds --test-pypi sage-cli
#   ./scripts/proprietary_publish.sh --clean --verbose sage-core

set -euo pipefail

# ========================================
# 配置和全局变量 Configuration and Globals
# ========================================

# 脚本目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/packages"

# 导入通用工具
source "$SCRIPT_DIR/common_utils.sh" 2>/dev/null || {
    echo "警告: 未找到 common_utils.sh，使用内置函数"
}

# 默认配置
DEFAULT_OUTPUT_DIR="$HOME/.sage/dist"
DRY_RUN=false
FORCE=false
TEST_PYPI=false
PUBLISH_ALL=false
VERBOSE=false
CLEAN_CACHE=false
NO_COMPILE=false
NO_UPLOAD=false
OUTPUT_DIR=""
PACKAGES_TO_PUBLISH=()

# 日志颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ========================================
# 工具函数 Utility Functions
# ========================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_verbose() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${PURPLE}[VERBOSE]${NC} $*"
    fi
}

show_help() {
    cat << EOF
${BOLD}一键闭源打包发布脚本 One-click Closed-source Publishing Script${NC}

${BOLD}用法 Usage:${NC}
  $0 [选项 options] [包名 package_names...]

${BOLD}选项 Options:${NC}
  -h, --help          显示帮助信息 Show help information
  -d, --dry-run       预演模式，不实际发布 Dry run mode, don't actually publish
  -f, --force         强制发布，跳过确认 Force publish, skip confirmation  
  -o, --output DIR    指定输出目录 Specify output directory (default: ~/.sage/dist)
  -t, --test-pypi     发布到测试PyPI Publish to Test PyPI
  -a, --all           发布所有包 Publish all packages
  -v, --verbose       详细输出 Verbose output
  -c, --clean         清理构建缓存 Clean build cache
  --no-compile        跳过编译步骤（仅打包） Skip compilation step, package only
  --no-upload         只编译打包，不上传 Only compile and package, don't upload

${BOLD}可发布的包 Available Packages:${NC}
$(find "$PACKAGES_DIR" -maxdepth 1 -type d -name "sage-*" | sort | sed 's|.*/||' | sed 's/^/  - /')

${BOLD}示例 Examples:${NC}
  # 预演模式发布所有包
  $0 --dry-run --all
  
  # 强制发布指定包到正式PyPI
  $0 --force sage-kernel sage-middleware
  
  # 发布到测试PyPI，指定输出目录
  $0 --output /tmp/builds --test-pypi sage-cli
  
  # 清理缓存并详细输出
  $0 --clean --verbose sage-core
  
  # 仅编译打包，不上传
  $0 --no-upload --all

${BOLD}环境要求 Requirements:${NC}
  - Python >= 3.10
  - sage-dev-toolkit 已安装
  - twine (用于上传PyPI)
  - 正确配置的PyPI凭据

${BOLD}更多信息 More Info:${NC}
  https://github.com/intellistream/SAGE/tree/main/dev-toolkit

EOF
}

check_prerequisites() {
    log_info "检查环境依赖 Checking prerequisites..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装"
        exit 1
    fi
    
    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_verbose "Python版本: $python_version"
    
    # 检查sage-dev工具
    if ! python3 -c "import sage_dev_toolkit" 2>/dev/null; then
        log_error "sage-dev-toolkit 未安装，请先安装"
        log_info "安装命令: cd $PROJECT_ROOT && pip install -e packages/sage-dev-toolkit"
        exit 1
    fi
    
    # 检查twine（如果需要上传）
    if [[ "$NO_UPLOAD" == false ]] && ! command -v twine &> /dev/null; then
        log_warning "未找到twine工具"
        log_info "安装命令: pip install twine"
        if [[ "$DRY_RUN" == false ]]; then
            exit 1
        fi
    fi
    
    log_success "环境检查通过"
}

get_available_packages() {
    find "$PACKAGES_DIR" -maxdepth 1 -type d -name "sage-*" | sort | sed 's|.*/||'
}

validate_packages() {
    local invalid_packages=()
    
    for package in "${PACKAGES_TO_PUBLISH[@]}"; do
        if [[ ! -d "$PACKAGES_DIR/$package" ]]; then
            invalid_packages+=("$package")
        fi
    done
    
    if [[ ${#invalid_packages[@]} -gt 0 ]]; then
        log_error "以下包不存在 Following packages don't exist:"
        printf '  - %s\n' "${invalid_packages[@]}"
        log_info "可用包 Available packages: $(get_available_packages | tr '\n' ' ')"
        exit 1
    fi
}

clean_build_cache() {
    if [[ "$CLEAN_CACHE" == false ]]; then
        return
    fi
    
    log_info "清理构建缓存 Cleaning build cache..."
    
    for package in "${PACKAGES_TO_PUBLISH[@]}"; do
        local package_dir="$PACKAGES_DIR/$package"
        log_verbose "清理包: $package"
        
        # 清理Python缓存
        find "$package_dir" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        find "$package_dir" -name "*.pyc" -delete 2>/dev/null || true
        
        # 清理构建目录
        rm -rf "$package_dir/dist" "$package_dir/build" 2>/dev/null || true
        find "$package_dir" -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
    done
    
    log_success "缓存清理完成"
}

get_package_version() {
    local package_dir="$1"
    local pyproject_file="$package_dir/pyproject.toml"
    
    if [[ -f "$pyproject_file" ]]; then
        python3 -c "
import sys
try:
    import tomli
    with open('$pyproject_file', 'rb') as f:
        data = tomli.load(f)
    print(data.get('project', {}).get('version', 'unknown'))
except ImportError:
    print('unknown')
except Exception:
    print('unknown')
"
    else
        echo "unknown"
    fi
}

confirm_publish() {
    if [[ "$FORCE" == true ]] || [[ "$DRY_RUN" == true ]]; then
        return 0
    fi
    
    echo
    log_info "即将发布以下闭源包 About to publish following proprietary packages:"
    echo
    
    for package in "${PACKAGES_TO_PUBLISH[@]}"; do
        local package_dir="$PACKAGES_DIR/$package"
        local version
        version=$(get_package_version "$package_dir")
        local target="PyPI"
        if [[ "$TEST_PYPI" == true ]]; then
            target="Test PyPI"
        fi
        echo -e "  ${BOLD}$package${NC} (v$version) → $target"
    done
    
    echo
    if [[ "$NO_UPLOAD" == true ]]; then
        echo -e "${YELLOW}注意: 仅编译打包，不会上传到PyPI${NC}"
    fi
    
    echo
    read -p "确认发布? Confirm publish? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "取消发布 Publishing cancelled"
        exit 0
    fi
}

publish_package() {
    local package="$1"
    local package_dir="$PACKAGES_DIR/$package"
    
    log_info "开始发布包 Starting to publish package: $package"
    log_verbose "包路径 Package path: $package_dir"
    
    # 构建命令参数
    local cmd_args=("python3" "-m" "sage_dev_toolkit.cli.main" "publish" "proprietary" "$package_dir")
    
    # 添加选项
    if [[ "$DRY_RUN" == true ]]; then
        cmd_args+=("--dry-run")
    else
        cmd_args+=("--no-dry-run")
    fi
    
    if [[ "$FORCE" == true ]]; then
        cmd_args+=("--force")
    fi
    
    if [[ -n "$OUTPUT_DIR" ]]; then
        cmd_args+=("--output" "$OUTPUT_DIR")
    fi
    
    log_verbose "执行命令 Executing command: ${cmd_args[*]}"
    
    # 执行发布命令
    if "${cmd_args[@]}"; then
        log_success "包发布成功 Package published successfully: $package"
        return 0
    else
        log_error "包发布失败 Package publishing failed: $package"
        return 1
    fi
}

upload_to_pypi() {
    if [[ "$NO_UPLOAD" == true ]] || [[ "$DRY_RUN" == true ]]; then
        log_info "跳过上传到PyPI Skipping PyPI upload"
        return 0
    fi
    
    local output_path="${OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}"
    
    if [[ ! -d "$output_path" ]]; then
        log_warning "输出目录不存在 Output directory doesn't exist: $output_path"
        return 0
    fi
    
    local wheel_files
    wheel_files=$(find "$output_path" -name "*.whl" -type f 2>/dev/null || true)
    
    if [[ -z "$wheel_files" ]]; then
        log_warning "未找到wheel文件 No wheel files found in: $output_path"
        return 0
    fi
    
    log_info "上传wheel文件到PyPI Uploading wheel files to PyPI..."
    
    local upload_cmd=("twine" "upload")
    
    if [[ "$TEST_PYPI" == true ]]; then
        upload_cmd+=("--repository" "testpypi")
        log_info "目标: Test PyPI"
    else
        log_info "目标: PyPI"
    fi
    
    # 添加所有wheel文件
    while IFS= read -r wheel_file; do
        if [[ -n "$wheel_file" ]]; then
            upload_cmd+=("$wheel_file")
            log_verbose "添加文件: $(basename "$wheel_file")"
        fi
    done <<< "$wheel_files"
    
    log_verbose "上传命令: ${upload_cmd[*]}"
    
    if "${upload_cmd[@]}"; then
        log_success "所有文件上传成功 All files uploaded successfully"
    else
        log_error "上传失败 Upload failed"
        return 1
    fi
}

generate_report() {
    local output_path="${OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}"
    local report_file="$output_path/publish_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成发布报告 Generating publish report..."
    
    mkdir -p "$output_path"
    
    cat > "$report_file" << EOF
SAGE 闭源包发布报告 SAGE Proprietary Package Publishing Report
======================================================

发布时间 Publish Time: $(date)
发布模式 Publish Mode: $(if [[ "$DRY_RUN" == true ]]; then echo "预演 Dry Run"; else echo "实际 Actual"; fi)
目标仓库 Target Repository: $(if [[ "$TEST_PYPI" == true ]]; then echo "Test PyPI"; else echo "PyPI"; fi)
输出目录 Output Directory: $output_path

发布包列表 Published Packages:
EOF

    for package in "${PACKAGES_TO_PUBLISH[@]}"; do
        local package_dir="$PACKAGES_DIR/$package"
        local version
        version=$(get_package_version "$package_dir")
        echo "  - $package (v$version)" >> "$report_file"
    done
    
    if [[ -d "$output_path" ]]; then
        echo "" >> "$report_file"
        echo "构建文件 Build Files:" >> "$report_file"
        find "$output_path" -name "*.whl" -type f -exec basename {} \; | sort | sed 's/^/  - /' >> "$report_file" || true
    fi
    
    echo "" >> "$report_file"
    echo "环境信息 Environment Info:" >> "$report_file"
    echo "  - Python: $(python3 --version)" >> "$report_file"
    echo "  - 系统 System: $(uname -s) $(uname -r)" >> "$report_file"
    echo "  - 用户 User: $(whoami)" >> "$report_file"
    echo "  - 主机 Host: $(hostname)" >> "$report_file"
    
    log_success "报告已生成 Report generated: $report_file"
}

# ========================================
# 主逻辑 Main Logic
# ========================================

parse_arguments() {
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
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -t|--test-pypi)
                TEST_PYPI=true
                shift
                ;;
            -a|--all)
                PUBLISH_ALL=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -c|--clean)
                CLEAN_CACHE=true
                shift
                ;;
            --no-compile)
                NO_COMPILE=true
                shift
                ;;
            --no-upload)
                NO_UPLOAD=true
                shift
                ;;
            -*)
                log_error "未知选项 Unknown option: $1"
                echo "使用 --help 查看帮助 Use --help for help"
                exit 1
                ;;
            *)
                PACKAGES_TO_PUBLISH+=("$1")
                shift
                ;;
        esac
    done
    
    # 设置输出目录默认值
    if [[ -z "$OUTPUT_DIR" ]]; then
        OUTPUT_DIR="$DEFAULT_OUTPUT_DIR"
    fi
    
    # 如果指定了--all，获取所有可用包
    if [[ "$PUBLISH_ALL" == true ]]; then
        mapfile -t PACKAGES_TO_PUBLISH < <(get_available_packages)
    fi
    
    # 如果没有指定任何包，显示帮助
    if [[ ${#PACKAGES_TO_PUBLISH[@]} -eq 0 ]]; then
        log_error "请指定要发布的包名，或使用 --all 发布所有包"
        echo "使用 --help 查看帮助"
        exit 1
    fi
}

main() {
    echo -e "${BOLD}${CYAN}🚀 SAGE 一键闭源打包发布脚本${NC}"
    echo -e "${CYAN}   One-click Closed-source Publishing Script${NC}"
    echo

    # 解析参数
    parse_arguments "$@"
    
    # 显示配置
    log_info "发布配置 Publishing Configuration:"
    echo "  📦 包数量 Package Count: ${#PACKAGES_TO_PUBLISH[@]}"
    echo "  📁 输出目录 Output Directory: $OUTPUT_DIR"
    echo "  🎯 目标仓库 Target Repository: $(if [[ "$TEST_PYPI" == true ]]; then echo "Test PyPI"; else echo "PyPI"; fi)"
    echo "  🔄 模式 Mode: $(if [[ "$DRY_RUN" == true ]]; then echo "预演 Dry Run"; else echo "实际 Actual"; fi)"
    
    if [[ "$VERBOSE" == true ]]; then
        echo "  📋 包列表 Package List: ${PACKAGES_TO_PUBLISH[*]}"
    fi
    echo

    # 检查环境
    check_prerequisites
    
    # 验证包
    validate_packages
    
    # 确认发布
    confirm_publish
    
    # 清理缓存
    clean_build_cache
    
    # 创建输出目录
    mkdir -p "$OUTPUT_DIR"
    
    # 发布各个包
    local failed_packages=()
    local successful_packages=()
    
    for package in "${PACKAGES_TO_PUBLISH[@]}"; do
        echo
        log_info "处理包 Processing package: $package"
        
        if publish_package "$package"; then
            successful_packages+=("$package")
        else
            failed_packages+=("$package")
            if [[ "$FORCE" == false ]]; then
                log_error "发布失败，停止处理后续包"
                break
            fi
        fi
    done
    
    # 上传到PyPI（如果启用）
    if [[ ${#successful_packages[@]} -gt 0 ]]; then
        echo
        upload_to_pypi
    fi
    
    # 生成报告
    generate_report
    
    # 显示结果
    echo
    echo -e "${BOLD}📊 发布结果总结 Publishing Results Summary${NC}"
    echo "=================================================="
    
    if [[ ${#successful_packages[@]} -gt 0 ]]; then
        echo -e "${GREEN}✅ 成功发布的包 Successfully published packages (${#successful_packages[@]}):${NC}"
        printf '   - %s\n' "${successful_packages[@]}"
    fi
    
    if [[ ${#failed_packages[@]} -gt 0 ]]; then
        echo -e "${RED}❌ 发布失败的包 Failed packages (${#failed_packages[@]}):${NC}"
        printf '   - %s\n' "${failed_packages[@]}"
    fi
    
    echo
    if [[ ${#failed_packages[@]} -eq 0 ]]; then
        log_success "🎉 所有包发布成功! All packages published successfully!"
        exit 0
    else
        log_error "部分包发布失败 Some packages failed to publish"
        exit 1
    fi
}

# 运行主函数
main "$@"
