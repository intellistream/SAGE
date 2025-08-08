#!/bin/bash

# SAGE 开源版本一键上传 PyPI 脚本
# 支持上传所有开源包到 PyPI

set -e  # 遇到错误立即退出

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/packages"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 显示帮助信息
show_help() {
    cat << EOF
SAGE PyPI 上传脚本

用法: $0 [选项] [包名...]

选项:
    -h, --help          显示此帮助信息
    -d, --dry-run       预演模式，不实际上传
    -t, --test          上传到 TestPyPI 而不是正式 PyPI
    -f, --force         强制重新构建包
    -v, --verbose       详细输出
    --skip-checks       跳过预检查
    --skip-build        跳过构建步骤，直接上传现有的包

包名 (如果不指定，将上传所有开源包):
    intsage-kernel         核心处理引擎
    intsage-middleware     中间件层
    intsage-userspace      用户空间库
    intsage                主包
    intsage-dev-toolkit    开发工具包
    intsage-frontend       Web前端

示例:
    $0                                      # 上传所有开源包
    $0 intsage-kernel intsage-frontend      # 只上传指定包
    $0 -t intsage-kernel                    # 上传到 TestPyPI
    $0 -d                                   # 预演模式
    $0 --skip-build sage-kernel     # 跳过构建，直接上传
EOF
}

# 默认配置
DRY_RUN=false
TEST_PYPI=false
FORCE_BUILD=false
VERBOSE=false
SKIP_CHECKS=false
SKIP_BUILD=false
PACKAGES_TO_UPLOAD=()

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
        -t|--test)
            TEST_PYPI=true
            shift
            ;;
        -f|--force)
            FORCE_BUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -*)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            PACKAGES_TO_UPLOAD+=("$1")
            shift
            ;;
    esac
done

# 定义开源包列表和路径
declare -A OPENSOURCE_PACKAGES=(
    ["intsage-kernel"]="$PACKAGES_DIR/sage-kernel"
    ["intsage-middleware"]="$PACKAGES_DIR/sage-middleware"
    ["intsage"]="$PACKAGES_DIR/sage"
)

# 如果没有指定包，则上传所有开源包
if [[ ${#PACKAGES_TO_UPLOAD[@]} -eq 0 ]]; then
    PACKAGES_TO_UPLOAD=($(printf '%s\n' "${!OPENSOURCE_PACKAGES[@]}" | sort))
fi

# 验证指定的包是否存在
for package in "${PACKAGES_TO_UPLOAD[@]}"; do
    if [[ ! -v OPENSOURCE_PACKAGES["$package"] ]]; then
        log_error "未知的包名: $package"
        log_info "可用的包: ${!OPENSOURCE_PACKAGES[*]}"
        exit 1
    fi
done

# 检查必要工具
check_requirements() {
    log_info "检查必要工具..."
    
    local missing_tools=()
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    # 检查 pip
    if ! python3 -m pip --version &> /dev/null; then
        missing_tools+=("pip")
    fi
    
    # 检查构建工具
    if ! python3 -c "import build" &> /dev/null; then
        log_warning "缺少 build 包，正在安装..."
        python3 -m pip install --upgrade build
    fi
    
    # 检查上传工具
    if ! python3 -c "import twine" &> /dev/null; then
        log_warning "缺少 twine 包，正在安装..."
        python3 -m pip install --upgrade twine
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "缺少必要工具: ${missing_tools[*]}"
        exit 1
    fi
    
    log_success "工具检查完成"
}

# 检查包配置
check_package_config() {
    local package_path="$1"
    local package_name="$2"
    
    log_info "检查包配置: $package_name"
    
    # 检查 pyproject.toml
    if [[ ! -f "$package_path/pyproject.toml" ]]; then
        log_error "$package_name: 缺少 pyproject.toml 文件"
        return 1
    fi
    
    # 检查版本信息
    local version=$(python3 -c "
import tomli
with open('$package_path/pyproject.toml', 'rb') as f:
    data = tomli.load(f)
    print(data.get('project', {}).get('version', 'unknown'))
" 2>/dev/null || echo "unknown")
    
    if [[ "$version" == "unknown" ]]; then
        log_error "$package_name: 无法读取版本信息"
        return 1
    fi
    
    log_info "$package_name: 版本 $version"
    
    # 检查 README
    if [[ ! -f "$package_path/README.md" ]]; then
        log_warning "$package_name: 缺少 README.md 文件"
    fi
    
    return 0
}

# 构建包
build_package() {
    local package_path="$1"
    local package_name="$2"
    
    log_info "构建包: $package_name"
    
    cd "$package_path"
    
    # 清理旧的构建文件
    if [[ "$FORCE_BUILD" == "true" ]]; then
        log_info "清理旧的构建文件..."
        rm -rf build/ dist/ *.egg-info/ src/*.egg-info/
    fi
    
    # 检查是否已经有构建产物
    if [[ -d "dist" && ! "$FORCE_BUILD" == "true" ]]; then
        local wheel_count=$(find dist -name "*.whl" 2>/dev/null | wc -l)
        if [[ $wheel_count -gt 0 ]]; then
            log_info "$package_name: 发现现有构建产物，跳过构建"
            return 0
        fi
    fi
    
    # 标准构建 (暂时禁用字节码编译)
    log_info "$package_name: 使用标准构建..."
    
    if [[ "$VERBOSE" == "true" ]]; then
        python3 -m build
    else
        python3 -m build > /dev/null 2>&1
    fi
    
    # 验证构建结果
    if [[ ! -d "dist" ]]; then
        log_error "$package_name: 构建失败，未找到 dist 目录"
        return 1
    fi
    
    local wheel_files=(dist/*.whl)
    local tar_files=(dist/*.tar.gz)
    
    if [[ ! -f "${wheel_files[0]}" ]]; then
        log_error "$package_name: 构建失败，未找到 wheel 文件"
        return 1
    fi
    
    log_success "$package_name: 构建完成"
    return 0
}

# 验证包
validate_package() {
    local package_path="$1"
    local package_name="$2"
    
    log_info "验证包: $package_name"
    
    cd "$package_path"
    
    # 使用 twine 检查包
    if [[ "$VERBOSE" == "true" ]]; then
        python3 -m twine check dist/*
    else
        python3 -m twine check dist/* > /dev/null 2>&1
    fi
    
    if [[ $? -ne 0 ]]; then
        log_error "$package_name: 包验证失败"
        return 1
    fi
    
    log_success "$package_name: 包验证通过"
    return 0
}

# 上传包
upload_package() {
    local package_path="$1"
    local package_name="$2"
    
    cd "$package_path"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[预演] 上传包: $package_name"
        log_info "[预演] 文件列表:"
        ls -la dist/
        return 0
    fi
    
    log_info "上传包: $package_name"
    
    # 选择上传目标
    local upload_cmd="python3 -m twine upload"
    if [[ "$TEST_PYPI" == "true" ]]; then
        upload_cmd+=" --repository testpypi"
        log_info "上传到 TestPyPI"
    else
        log_info "上传到 PyPI"
    fi
    
    # 执行上传
    if [[ "$VERBOSE" == "true" ]]; then
        $upload_cmd dist/*
    else
        $upload_cmd dist/* 2>/dev/null
    fi
    
    if [[ $? -eq 0 ]]; then
        log_success "$package_name: 上传完成"
    else
        log_error "$package_name: 上传失败"
        return 1
    fi
    
    return 0
}

# 主函数
main() {
    log_info "SAGE PyPI 上传脚本启动"
    log_info "工作目录: $PROJECT_ROOT"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "预演模式：不会实际上传包"
    fi
    
    if [[ "$TEST_PYPI" == "true" ]]; then
        log_warning "将上传到 TestPyPI"
    fi
    
    # 检查必要工具
    if [[ "$SKIP_CHECKS" != "true" ]]; then
        check_requirements
    fi
    
    # 处理每个包
    local failed_packages=()
    local success_packages=()
    
    for package in "${PACKAGES_TO_UPLOAD[@]}"; do
        local package_path="${OPENSOURCE_PACKAGES[$package]}"
        
        log_info "处理包: $package ($package_path)"
        
        # 检查包路径是否存在
        if [[ ! -d "$package_path" ]]; then
            log_error "$package: 路径不存在 $package_path"
            failed_packages+=("$package")
            continue
        fi
        
        # 检查包配置
        if [[ "$SKIP_CHECKS" != "true" ]]; then
            if ! check_package_config "$package_path" "$package"; then
                failed_packages+=("$package")
                continue
            fi
        fi
        
        # 构建包
        if [[ "$SKIP_BUILD" != "true" ]]; then
            if ! build_package "$package_path" "$package"; then
                failed_packages+=("$package")
                continue
            fi
        fi
        
        # 验证包
        if [[ "$SKIP_CHECKS" != "true" ]]; then
            if ! validate_package "$package_path" "$package"; then
                failed_packages+=("$package")
                continue
            fi
        fi
        
        # 上传包
        if ! upload_package "$package_path" "$package"; then
            failed_packages+=("$package")
            continue
        fi
        
        success_packages+=("$package")
    done
    
    # 显示总结
    echo
    log_info "上传总结:"
    
    if [[ ${#success_packages[@]} -gt 0 ]]; then
        log_success "成功上传 ${#success_packages[@]} 个包:"
        for package in "${success_packages[@]}"; do
            echo "  ✓ $package"
        done
    fi
    
    if [[ ${#failed_packages[@]} -gt 0 ]]; then
        log_error "失败 ${#failed_packages[@]} 个包:"
        for package in "${failed_packages[@]}"; do
            echo "  ✗ $package"
        done
        exit 1
    fi
    
    if [[ "$DRY_RUN" != "true" ]]; then
        log_success "所有包上传完成！"
    else
        log_info "预演完成！"
    fi
}

# 检查是否在正确的目录
if [[ ! -d "$PACKAGES_DIR" ]]; then
    log_error "未找到 packages 目录，请确保在 SAGE 项目根目录运行此脚本"
    exit 1
fi

# 运行主函数
main "$@"
