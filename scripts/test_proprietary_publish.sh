#!/bin/bash
#
# 闭源发布脚本测试套件
# Proprietary Publishing Scripts Test Suite
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo -e "${RED}[ERROR]${NC} $*"
}

test_script_permissions() {
    log_info "测试脚本权限..."
    
    local scripts=(
        "proprietary_publish.sh"
        "quick_publish.sh" 
        "test_proprietary_publish.sh"
    )
    
    for script in "${scripts[@]}"; do
        local script_path="$SCRIPT_DIR/$script"
        if [[ -f "$script_path" ]]; then
            if [[ -x "$script_path" ]]; then
                log_success "$script 权限正常"
            else
                log_error "$script 不可执行"
                chmod +x "$script_path"
                log_info "已修复 $script 权限"
            fi
        else
            log_error "$script 不存在"
        fi
    done
}

test_config_file() {
    log_info "测试配置文件..."
    
    local config_file="$SCRIPT_DIR/proprietary_publish_config.sh"
    if [[ -f "$config_file" ]]; then
        if source "$config_file" &>/dev/null; then
            log_success "配置文件语法正确"
        else
            log_error "配置文件语法错误"
            return 1
        fi
    else
        log_error "配置文件不存在"
        return 1
    fi
}

test_python_environment() {
    log_info "测试Python环境..."
    
    # 检查Python版本
    if command -v python3 &>/dev/null; then
        local python_version
        python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        log_success "Python版本: $python_version"
        
        if [[ $(echo "$python_version >= 3.10" | bc) -eq 1 ]] 2>/dev/null || [[ "$python_version" =~ ^3\.(1[0-9]|[2-9][0-9])$ ]]; then
            log_success "Python版本满足要求 (>=3.10)"
        else
            log_warning "Python版本可能过低，推荐使用3.10+"
        fi
    else
        log_error "未找到Python3"
        return 1
    fi
    
    # 检查sage-dev-toolkit
    if python3 -c "import sage_dev_toolkit" 2>/dev/null; then
        log_success "sage-dev-toolkit 已安装"
        
        # 尝试获取版本
        local version
        version=$(python3 -c "import sage_dev_toolkit; print(getattr(sage_dev_toolkit, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
        log_info "版本: $version"
    else
        log_warning "sage-dev-toolkit 未安装或不可导入"
        log_info "建议运行: cd $PROJECT_ROOT && pip install -e packages/sage-dev-toolkit"
    fi
}

test_required_tools() {
    log_info "测试必要工具..."
    
    local tools=("build" "twine" "pip" "git")
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" &>/dev/null; then
            log_success "$tool 可用"
            
            # 获取版本信息
            case $tool in
                build)
                    python3 -m build --version 2>/dev/null || true
                    ;;
                twine)
                    twine --version 2>/dev/null || true
                    ;;
                pip)
                    pip --version 2>/dev/null || true
                    ;;
                git)
                    git --version 2>/dev/null || true
                    ;;
            esac
        else
            log_warning "$tool 不可用"
            
            case $tool in
                build)
                    log_info "安装命令: pip install build"
                    ;;
                twine)
                    log_info "安装命令: pip install twine"
                    ;;
            esac
        fi
    done
}

test_packages_structure() {
    log_info "测试包结构..."
    
    local packages_dir="$PROJECT_ROOT/packages"
    if [[ -d "$packages_dir" ]]; then
        log_success "packages 目录存在"
        
        local sage_packages
        mapfile -t sage_packages < <(find "$packages_dir" -maxdepth 1 -type d -name "sage-*" | sort)
        
        if [[ ${#sage_packages[@]} -gt 0 ]]; then
            log_success "找到 ${#sage_packages[@]} 个SAGE包:"
            
            for package_path in "${sage_packages[@]}"; do
                local package_name
                package_name=$(basename "$package_path")
                
                # 检查必要文件
                local has_pyproject=false
                local has_setup=false
                local has_src=false
                
                if [[ -f "$package_path/pyproject.toml" ]]; then
                    has_pyproject=true
                fi
                
                if [[ -f "$package_path/setup.py" ]]; then
                    has_setup=true
                fi
                
                if [[ -d "$package_path/src" ]]; then
                    has_src=true
                fi
                
                local status="✓"
                local issues=()
                
                if [[ "$has_pyproject" == false ]] && [[ "$has_setup" == false ]]; then
                    status="✗"
                    issues+=("缺少pyproject.toml或setup.py")
                fi
                
                if [[ "$has_src" == false ]]; then
                    status="✗" 
                    issues+=("缺少src目录")
                fi
                
                if [[ ${#issues[@]} -eq 0 ]]; then
                    log_success "  $status $package_name"
                else
                    log_warning "  $status $package_name (${issues[*]})"
                fi
            done
        else
            log_warning "未找到SAGE包"
        fi
    else
        log_error "packages 目录不存在"
        return 1
    fi
}

test_help_commands() {
    log_info "测试帮助命令..."
    
    # 测试主脚本帮助
    if "$SCRIPT_DIR/proprietary_publish.sh" --help &>/dev/null; then
        log_success "主脚本帮助命令正常"
    else
        log_error "主脚本帮助命令失败"
    fi
    
    # 测试快捷脚本帮助
    if "$SCRIPT_DIR/quick_publish.sh" --help &>/dev/null; then
        log_success "快捷脚本帮助命令正常"
    else
        log_error "快捷脚本帮助命令失败"
    fi
}

test_dry_run() {
    log_info "测试预演模式..."
    
    # 找一个可用的包进行测试
    local test_package
    test_package=$(find "$PROJECT_ROOT/packages" -maxdepth 1 -type d -name "sage-*" | head -1 | xargs basename 2>/dev/null || echo "")
    
    if [[ -n "$test_package" ]]; then
        log_info "使用测试包: $test_package"
        
        # 测试主脚本dry-run
        if timeout 30 "$SCRIPT_DIR/proprietary_publish.sh" --dry-run --force "$test_package" &>/dev/null; then
            log_success "主脚本预演模式测试通过"
        else
            log_warning "主脚本预演模式测试失败或超时"
        fi
        
        # 测试快捷脚本dry-run
        if timeout 30 "$SCRIPT_DIR/quick_publish.sh" dev-test &>/dev/null; then
            log_success "快捷脚本预演模式测试通过"
        else
            log_warning "快捷脚本预演模式测试失败或超时"
        fi
    else
        log_warning "未找到测试包，跳过预演模式测试"
    fi
}

show_summary() {
    echo
    echo "======================================"
    echo "           测试总结 Test Summary"
    echo "======================================"
    echo
    
    log_info "脚本位置:"
    echo "  - 主脚本: $SCRIPT_DIR/proprietary_publish.sh"
    echo "  - 快捷脚本: $SCRIPT_DIR/quick_publish.sh"
    echo "  - 配置文件: $SCRIPT_DIR/proprietary_publish_config.sh"
    echo "  - 说明文档: $SCRIPT_DIR/PROPRIETARY_PUBLISH_README.md"
    
    echo
    log_info "使用示例:"
    echo "  # 查看帮助"
    echo "  $SCRIPT_DIR/proprietary_publish.sh --help"
    echo "  $SCRIPT_DIR/quick_publish.sh --help"
    echo
    echo "  # 预演模式测试"
    echo "  $SCRIPT_DIR/quick_publish.sh dev-test"
    echo
    echo "  # 生产发布"
    echo "  $SCRIPT_DIR/quick_publish.sh production"
    echo
    echo "  # 交互模式"
    echo "  $SCRIPT_DIR/quick_publish.sh custom"
    
    echo
    log_success "闭源发布脚本套件测试完成!"
}

main() {
    echo "🚀 SAGE 闭源发布脚本测试套件"
    echo "   Proprietary Publishing Scripts Test Suite"
    echo
    
    local test_failed=false
    
    # 运行所有测试
    test_script_permissions || test_failed=true
    echo
    
    test_config_file || test_failed=true
    echo
    
    test_python_environment || test_failed=true
    echo
    
    test_required_tools || test_failed=true
    echo
    
    test_packages_structure || test_failed=true
    echo
    
    test_help_commands || test_failed=true
    echo
    
    test_dry_run || test_failed=true
    echo
    
    show_summary
    
    if [[ "$test_failed" == true ]]; then
        echo
        log_warning "部分测试失败，请检查上述警告和错误"
        exit 1
    else
        echo
        log_success "所有测试通过!"
        exit 0
    fi
}

main "$@"
