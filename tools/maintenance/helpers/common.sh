#!/bin/bash
# 通用辅助函数库
# 被其他脚本引用

# 颜色和样式定义
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export MAGENTA='\033[0;35m'
export DIM='\033[0;2m'
export BOLD='\033[1m'
export NC='\033[0m'

# Emoji
export CHECK='✅'
export CROSS='❌'
export INFO='ℹ️'
export WARNING='⚠️'
export ROCKET='🚀'
export WRENCH='🔧'
export BROOM='🧹'
export SHIELD='🛡️'
export PACKAGE='📦'
export MAGNIFIER='🔍'

# ============================================================================
# 日志函数
# ============================================================================

log_info() {
    echo -e "${BLUE}${INFO} $*${NC}"
}

log_success() {
    echo -e "${GREEN}${CHECK} $*${NC}"
}

log_warning() {
    echo -e "${YELLOW}${WARNING} $*${NC}"
}

log_error() {
    echo -e "${RED}${CROSS} $*${NC}" >&2
}

log_debug() {
    if [ "${VERBOSE}" = "true" ]; then
        echo -e "${DIM}[DEBUG] $*${NC}"
    fi
}

# ============================================================================
# Git 辅助函数
# ============================================================================

# 获取当前分支
get_current_branch() {
    git rev-parse --abbrev-ref HEAD
}

# 检查是否在 Git 仓库中
is_git_repo() {
    git rev-parse --git-dir > /dev/null 2>&1
}

# 获取仓库根目录
get_repo_root() {
    git rev-parse --show-toplevel 2>/dev/null
}

# 检查工作区是否干净
is_working_tree_clean() {
    git diff-index --quiet HEAD -- 2>/dev/null
}

# ============================================================================
# 确认提示
# ============================================================================

confirm() {
    local message="$1"
    local default="${2:-n}"

    if [ "${FORCE}" = "true" ]; then
        return 0
    fi

    local prompt
    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi

    read -p "$(echo -e ${YELLOW}${message} ${prompt}: ${NC})" response
    response=${response:-$default}

    [[ "$response" =~ ^[Yy]$ ]]
}

# ============================================================================
# 进度显示
# ============================================================================

spinner() {
    local pid=$1
    local message="$2"
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

    while kill -0 $pid 2>/dev/null; do
        local temp=${spinstr#?}
        printf "\r${BLUE}%c${NC} %s" "$spinstr" "$message"
        local spinstr=$temp${spinstr%"$temp"}
        sleep 0.1
    done
    printf "\r${GREEN}${CHECK}${NC} %s\n" "$message"
}

# ============================================================================
# 文件和目录辅助函数
# ============================================================================

# 安全删除目录
safe_remove_dir() {
    local dir="$1"
    if [ -d "$dir" ]; then
        log_debug "删除目录: $dir"
        rm -rf "$dir"
    fi
}

# 安全删除文件
safe_remove_file() {
    local file="$1"
    if [ -f "$file" ]; then
        log_debug "删除文件: $file"
        rm -f "$file"
    fi
}

# 检查命令是否存在
command_exists() {
    command -v "$1" &> /dev/null
}

# ============================================================================
# 错误处理
# ============================================================================

# 错误退出
die() {
    log_error "$*"
    exit 1
}

# 设置错误处理
setup_error_handling() {
    set -euo pipefail
    trap 'die "脚本在第 $LINENO 行执行失败"' ERR
}
