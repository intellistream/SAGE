#!/bin/bash
# SAGE 安装脚本 - 颜色和样式定义
# 统一管理所有颜色和 Unicode 符号

# 强制告诉 VS Code/xterm.js 支持 ANSI 和 256 色
export TERM=xterm-256color

# 颜色和样式
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export RED='\033[0;31m'
export BLUE='\033[1;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export WHITE='\033[1;37m'
export GRAY='\033[0;37m'
export BOLD='\033[1m'
export DIM='\033[2m'
export NC='\033[0m' # No Color

# Unicode 符号 - 基础定义
_ROCKET_BASE="🚀"
_GEAR_BASE="⚙️"
_CHECK_BASE="✅"
_CROSS_BASE="❌"
_WARNING_BASE="⚠️"
_INFO_BASE="ℹ️"
_SPARKLES_BASE="✨"
_SUCCESS_BASE="✅"

# 根据环境设置Unicode符号的函数
setup_unicode_symbols() {
    # 检查是否需要偏移（这个函数会在output_formatter.sh中定义）
    if command -v detect_vscode_offset_requirement >/dev/null 2>&1; then
        detect_vscode_offset_requirement
    fi

    # 根据VSCODE_OFFSET_ENABLED状态设置符号
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        # VS Code环境：为Unicode符号添加前后空格
        export ROCKET=" ${_ROCKET_BASE}  "
        export GEAR=" ${_GEAR_BASE}  "
        export CHECK=" ${_CHECK_BASE} "
        export CROSS=" ${_CROSS_BASE} "
        export WARNING=" ${_WARNING_BASE}  "
        export INFO=" ${_INFO_BASE}  "
        export SPARKLES=" ${_SPARKLES_BASE}  "
        export SUCCESS=" ${_SUCCESS_BASE}"
    else
        # 普通终端：不添加额外空格
        export ROCKET="$_ROCKET_BASE"
        export GEAR="$_GEAR_BASE"
        export CHECK="$_CHECK_BASE"
        export CROSS="$_CROSS_BASE"
        export WARNING="$_WARNING_BASE"
        export INFO="$_INFO_BASE"
        export SPARKLES="$_SPARKLES_BASE"
        export SUCCESS="$_SUCCESS_BASE"
    fi
}

# 允许用户自定义符号偏移
set_symbol_offset() {
    local pre_spaces="${1:-2}"  # 默认前置2个空格
    local post_spaces="${2:-2}" # 默认后置2个空格

    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        local pre_padding=$(printf "%*s" "$pre_spaces" "")
        local post_padding=$(printf "%*s" "$post_spaces" "")

        export ROCKET="${pre_padding}${_ROCKET_BASE}${post_padding}"
        export GEAR="${pre_padding}${_GEAR_BASE}${post_padding}"
        export CHECK="${pre_padding}${_CHECK_BASE}${post_padding}"
        export CROSS="${pre_padding}${_CROSS_BASE}${post_padding}"
        export WARNING="${pre_padding}${_WARNING_BASE}${post_padding}"
        export INFO="${pre_padding}${_INFO_BASE}${post_padding}"
        export SPARKLES="${pre_padding}${_SPARKLES_BASE}${post_padding}"
        export SUCCESS="${pre_padding}${_SUCCESS_BASE}${post_padding}"
    fi
}
