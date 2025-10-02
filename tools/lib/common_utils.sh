#!/bin/bash

# SAGE 项目通用工具模块
# 提供常用的工具函数

# 引入日志模块
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/logging.sh"

# 检查命令是否存在（必需）
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        exit 1
    fi
}

# 检查命令是否存在（可选）
check_command_optional() {
    if ! command -v $1 &> /dev/null; then
        return 1
    fi
    return 0
}

# 检查文件是否存在
check_file_exists() {
    local file_path="$1"
    local description="${2:-文件}"
    
    if [ ! -f "$file_path" ]; then
        print_error "$description 不存在: $file_path"
        return 1
    fi
    return 0
}

# 检查目录是否存在
check_dir_exists() {
    local dir_path="$1"
    local description="${2:-目录}"
    
    if [ ! -d "$dir_path" ]; then
        print_error "$description 不存在: $dir_path"
        return 1
    fi
    return 0
}

# 获取脚本绝对路径
get_script_dir() {
    echo "$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
}

# 查找项目根目录
find_project_root() {
    local current_dir="${1:-$(pwd)}"
    local marker_file="${2:-pyproject.toml}"
    
    while [ "$current_dir" != "/" ]; do
        if [ -f "$current_dir/$marker_file" ]; then
            echo "$current_dir"
            return 0
        fi
        current_dir=$(dirname "$current_dir")
    done
    
    return 1
}

# 验证项目目录结构
validate_project_structure() {
    local project_root="$1"
    local required_files=("pyproject.toml")
    local required_dirs=("packages")
    
    for file in "${required_files[@]}"; do
        if ! check_file_exists "$project_root/$file" "项目文件 $file"; then
            return 1
        fi
    done
    
    for dir in "${required_dirs[@]}"; do
        if ! check_dir_exists "$project_root/$dir" "项目目录 $dir"; then
            return 1
        fi
    done
    
    return 0
}

# 设置项目环境变量
setup_project_env() {
    local project_root="$1"
    
    export SAGE_PROJECT_ROOT="$project_root"
    export SAGE_PACKAGES_DIR="$project_root/packages"
    export SAGE_SCRIPTS_DIR="$project_root/scripts"
    export SAGE_DOCS_DIR="$project_root/docs"
    export SAGE_TESTS_DIR="$project_root/tests"
    
    print_debug "设置项目环境变量:"
    print_debug "  SAGE_PROJECT_ROOT=$SAGE_PROJECT_ROOT"
    print_debug "  SAGE_PACKAGES_DIR=$SAGE_PACKAGES_DIR"
    print_debug "  SAGE_SCRIPTS_DIR=$SAGE_SCRIPTS_DIR"
}

# 执行命令并捕获输出
run_command() {
    local cmd="$1"
    local description="${2:-执行命令}"
    
    print_debug "执行命令: $cmd"
    
    if eval "$cmd"; then
        print_debug "$description 成功"
        return 0
    else
        local exit_code=$?
        print_error "$description 失败 (退出码: $exit_code)"
        return $exit_code
    fi
}

# 安全地改变目录
safe_cd() {
    local target_dir="$1"
    local description="${2:-切换到目录}"
    
    if ! check_dir_exists "$target_dir" "$description"; then
        return 1
    fi
    
    cd "$target_dir" || {
        print_error "无法切换到目录: $target_dir"
        return 1
    }
    
    print_debug "已切换到目录: $(pwd)"
    return 0
}

# 备份文件
backup_file() {
    local file_path="$1"
    local backup_suffix="${2:-.backup.$(date +%Y%m%d_%H%M%S)}"
    
    if [ -f "$file_path" ]; then
        local backup_path="${file_path}${backup_suffix}"
        cp "$file_path" "$backup_path"
        print_status "已备份文件: $file_path -> $backup_path"
    fi
}

# 创建目录（如果不存在）
ensure_dir() {
    local dir_path="$1"
    
    if [ ! -d "$dir_path" ]; then
        mkdir -p "$dir_path"
        print_debug "创建目录: $dir_path"
    fi
}

# 检查磁盘空间
check_disk_space() {
    local path="${1:-.}"
    local required_mb="${2:-1000}"
    
    local available_mb=$(df "$path" | awk 'NR==2 {print int($4/1024)}')
    
    if [ "$available_mb" -lt "$required_mb" ]; then
        print_warning "磁盘空间不足: 需要 ${required_mb}MB，可用 ${available_mb}MB"
        return 1
    fi
    
    print_debug "磁盘空间检查通过: 可用 ${available_mb}MB"
    return 0
}

# 检查网络连接
check_network() {
    local test_url="${1:-https://github.com}"
    
    if check_command_optional curl; then
        if curl -s --head "$test_url" > /dev/null; then
            print_debug "网络连接正常"
            return 0
        fi
    elif check_command_optional wget; then
        if wget -q --spider "$test_url"; then
            print_debug "网络连接正常"
            return 0
        fi
    fi
    
    print_warning "网络连接检查失败"
    return 1
}

# 等待用户按键
wait_for_key() {
    local message="${1:-按任意键继续...}"
    echo -n "$message"
    read -n 1 -s
    echo
}

# 显示帮助信息
show_usage() {
    local script_name="$1"
    local description="$2"
    shift 2
    local options=("$@")
    
    echo "用法: $script_name [选项]"
    echo
    echo "描述: $description"
    echo
    if [ ${#options[@]} -gt 0 ]; then
        echo "选项:"
        for option in "${options[@]}"; do
            echo "  $option"
        done
        echo
    fi
}
