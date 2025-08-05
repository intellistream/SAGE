#!/bin/bash

# SAGE 版本管理脚本
# 用于管理所有开源包的版本号

set -e

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_DIR="$PROJECT_ROOT/packages"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

show_help() {
    cat << EOF
SAGE 版本管理脚本

用法: $0 [选项] [命令] [包名...]

命令:
    show                显示所有包的当前版本
    bump [type]         增加版本号 (patch|minor|major)
    set <version>       设置指定版本号
    sync                同步所有包到相同版本
    check               检查版本一致性

选项:
    -h, --help          显示此帮助信息
    -d, --dry-run       预演模式，不实际修改文件
    -v, --verbose       详细输出
    --all               操作所有开源包
    --git-tag           创建 git 标签

包名 (如果不指定 --all，必须指定包名):
    sage-kernel, sage-middleware, sage-userspace, sage
    sage-dev-toolkit, sage-frontend

示例:
    $0 show                                 # 显示所有版本
    $0 bump patch sage-kernel               # 增加 sage-kernel 的补丁版本
    $0 bump minor --all                     # 增加所有包的次要版本
    $0 set 1.1.0 sage-frontend              # 设置 sage-frontend 版本为 1.1.0
    $0 sync                                 # 同步所有包版本
    $0 check                                # 检查版本一致性
EOF
}

# 默认配置
DRY_RUN=false
VERBOSE=false
ALL_PACKAGES=false
GIT_TAG=false
COMMAND=""
VERSION_TYPE=""
NEW_VERSION=""
PACKAGES_TO_PROCESS=()

# 开源包列表
declare -A OPENSOURCE_PACKAGES=(
    ["sage-kernel"]="$PACKAGES_DIR/sage-kernel"
    ["sage-middleware"]="$PACKAGES_DIR/sage-middleware"
    ["sage-userspace"]="$PACKAGES_DIR/sage-userspace"
    ["sage"]="$PACKAGES_DIR/sage"
    ["sage-dev-toolkit"]="$PACKAGES_DIR/sage-tools/sage-dev-toolkit"
    ["sage-frontend"]="$PACKAGES_DIR/sage-tools/sage-frontend"
)

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
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --all)
            ALL_PACKAGES=true
            shift
            ;;
        --git-tag)
            GIT_TAG=true
            shift
            ;;
        show|bump|set|sync|check)
            COMMAND="$1"
            shift
            ;;
        patch|minor|major)
            VERSION_TYPE="$1"
            shift
            ;;
        [0-9]*.[0-9]*.[0-9]*)
            NEW_VERSION="$1"
            shift
            ;;
        -*)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            PACKAGES_TO_PROCESS+=("$1")
            shift
            ;;
    esac
done

# 验证命令
if [[ -z "$COMMAND" ]]; then
    log_error "必须指定命令"
    show_help
    exit 1
fi

# 如果指定了 --all，使用所有包
if [[ "$ALL_PACKAGES" == "true" ]]; then
    PACKAGES_TO_PROCESS=($(printf '%s\n' "${!OPENSOURCE_PACKAGES[@]}" | sort))
fi

# 读取包版本
get_package_version() {
    local package_path="$1"
    
    if [[ ! -f "$package_path/pyproject.toml" ]]; then
        echo "unknown"
        return
    fi
    
    python3 -c "
import tomli
try:
    with open('$package_path/pyproject.toml', 'rb') as f:
        data = tomli.load(f)
        print(data.get('project', {}).get('version', 'unknown'))
except:
    print('unknown')
" 2>/dev/null || echo "unknown"
}

# 设置包版本
set_package_version() {
    local package_path="$1"
    local new_version="$2"
    local package_name="$3"
    
    if [[ ! -f "$package_path/pyproject.toml" ]]; then
        log_error "$package_name: pyproject.toml 不存在"
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[预演] $package_name: 版本设置为 $new_version"
        return 0
    fi
    
    # 使用 Python 脚本更新版本
    python3 -c "
import tomli
import tomli_w

with open('$package_path/pyproject.toml', 'rb') as f:
    data = tomli.load(f)

if 'project' not in data:
    data['project'] = {}

data['project']['version'] = '$new_version'

with open('$package_path/pyproject.toml', 'wb') as f:
    tomli_w.dump(data, f)
"
    
    if [[ $? -eq 0 ]]; then
        log_success "$package_name: 版本更新为 $new_version"
    else
        log_error "$package_name: 版本更新失败"
        return 1
    fi
}

# 增加版本号
bump_version() {
    local current_version="$1"
    local bump_type="$2"
    
    if [[ "$current_version" == "unknown" ]]; then
        echo "1.0.0"
        return
    fi
    
    python3 -c "
import re

version = '$current_version'
bump_type = '$bump_type'

# 解析版本号
match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version)
if not match:
    print('1.0.0')
    exit()

major, minor, patch = map(int, match.groups())

if bump_type == 'major':
    major += 1
    minor = 0
    patch = 0
elif bump_type == 'minor':
    minor += 1
    patch = 0
elif bump_type == 'patch':
    patch += 1

print(f'{major}.{minor}.{patch}')
"
}

# 显示版本信息
show_versions() {
    log_info "当前版本信息:"
    echo
    
    printf "%-20s %-15s %-50s\n" "包名" "版本" "路径"
    printf "%-20s %-15s %-50s\n" "----" "----" "----"
    
    for package in $(printf '%s\n' "${!OPENSOURCE_PACKAGES[@]}" | sort); do
        local package_path="${OPENSOURCE_PACKAGES[$package]}"
        local version=$(get_package_version "$package_path")
        printf "%-20s %-15s %-50s\n" "$package" "$version" "$package_path"
    done
    echo
}

# 检查版本一致性
check_versions() {
    log_info "检查版本一致性..."
    
    local versions=()
    local inconsistent=false
    
    for package in $(printf '%s\n' "${!OPENSOURCE_PACKAGES[@]}" | sort); do
        local package_path="${OPENSOURCE_PACKAGES[$package]}"
        local version=$(get_package_version "$package_path")
        versions+=("$version")
        
        if [[ "$version" == "unknown" ]]; then
            log_warning "$package: 无法读取版本信息"
            inconsistent=true
        fi
    done
    
    # 检查是否所有版本都相同
    local first_version="${versions[0]}"
    for version in "${versions[@]}"; do
        if [[ "$version" != "$first_version" && "$version" != "unknown" && "$first_version" != "unknown" ]]; then
            inconsistent=true
            break
        fi
    done
    
    if [[ "$inconsistent" == "true" ]]; then
        log_warning "发现版本不一致"
        show_versions
    else
        log_success "所有包版本一致: $first_version"
    fi
}

# 同步版本
sync_versions() {
    log_info "同步版本..."
    
    # 获取最常见的版本
    local versions=()
    for package in "${!OPENSOURCE_PACKAGES[@]}"; do
        local package_path="${OPENSOURCE_PACKAGES[$package]}"
        local version=$(get_package_version "$package_path")
        if [[ "$version" != "unknown" ]]; then
            versions+=("$version")
        fi
    done
    
    if [[ ${#versions[@]} -eq 0 ]]; then
        log_error "没有找到有效的版本信息"
        exit 1
    fi
    
    # 找到最常见的版本
    local target_version=$(printf '%s\n' "${versions[@]}" | sort | uniq -c | sort -nr | head -1 | awk '{print $2}')
    
    log_info "目标版本: $target_version"
    
    # 更新所有包到目标版本
    for package in "${!OPENSOURCE_PACKAGES[@]}"; do
        local package_path="${OPENSOURCE_PACKAGES[$package]}"
        local current_version=$(get_package_version "$package_path")
        
        if [[ "$current_version" != "$target_version" ]]; then
            set_package_version "$package_path" "$target_version" "$package"
        else
            log_info "$package: 版本已是 $target_version"
        fi
    done
}

# 创建 git 标签
create_git_tag() {
    local version="$1"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[预演] 创建 git 标签: v$version"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    if git tag | grep -q "v$version"; then
        log_warning "标签 v$version 已存在"
        return 0
    fi
    
    git tag "v$version"
    log_success "创建 git 标签: v$version"
}

# 主函数
main() {
    case "$COMMAND" in
        show)
            show_versions
            ;;
        check)
            check_versions
            ;;
        sync)
            sync_versions
            ;;
        bump)
            if [[ -z "$VERSION_TYPE" ]]; then
                log_error "bump 命令需要指定版本类型 (patch|minor|major)"
                exit 1
            fi
            
            if [[ ${#PACKAGES_TO_PROCESS[@]} -eq 0 ]]; then
                log_error "必须指定要更新的包名或使用 --all"
                exit 1
            fi
            
            for package in "${PACKAGES_TO_PROCESS[@]}"; do
                local package_path="${OPENSOURCE_PACKAGES[$package]}"
                if [[ -z "$package_path" ]]; then
                    log_error "未知包名: $package"
                    continue
                fi
                
                local current_version=$(get_package_version "$package_path")
                local new_version=$(bump_version "$current_version" "$VERSION_TYPE")
                
                set_package_version "$package_path" "$new_version" "$package"
                
                if [[ "$GIT_TAG" == "true" && "$ALL_PACKAGES" == "true" ]]; then
                    create_git_tag "$new_version"
                fi
            done
            ;;
        set)
            if [[ -z "$NEW_VERSION" ]]; then
                log_error "set 命令需要指定新版本号"
                exit 1
            fi
            
            if [[ ${#PACKAGES_TO_PROCESS[@]} -eq 0 ]]; then
                log_error "必须指定要更新的包名或使用 --all"
                exit 1
            fi
            
            for package in "${PACKAGES_TO_PROCESS[@]}"; do
                local package_path="${OPENSOURCE_PACKAGES[$package]}"
                if [[ -z "$package_path" ]]; then
                    log_error "未知包名: $package"
                    continue
                fi
                
                set_package_version "$package_path" "$NEW_VERSION" "$package"
            done
            
            if [[ "$GIT_TAG" == "true" ]]; then
                create_git_tag "$NEW_VERSION"
            fi
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 检查必要工具
if ! python3 -c "import tomli, tomli_w" &> /dev/null; then
    log_warning "缺少必要的 Python 包，正在安装..."
    python3 -m pip install tomli tomli-w
fi

# 运行主函数
main
