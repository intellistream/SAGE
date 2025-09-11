#!/bin/bash
# SAGE 安装脚本 - 输出格式化模块
# 处理不同环境下的输出格式化和偏移问题

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/colors.sh"

# 全局变量
OUTPUT_PREFIX=""
VSCODE_OFFSET_ENABLED=false

# 检测是否需要 VS Code 偏移
detect_vscode_offset_requirement() {
    # 静默检查系统环境
    local needs_offset=false
    
    # 检查操作系统
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        local os_id="$ID"
        local version_id="$VERSION_ID"
        
        # 检查是否为 Ubuntu 22.04
        if [ "$os_id" = "ubuntu" ] && [ "$version_id" = "22.04" ]; then
            # 检查 CPU 架构
            local cpu_arch=$(uname -m)
            if [ "$cpu_arch" = "x86_64" ]; then
                # 检查是否在 Docker 中
                if [ -f "/.dockerenv" ] || grep -q "docker" /proc/1/cgroup 2>/dev/null; then
                    needs_offset=true
                fi
            fi
        fi
    fi
    
    if [ "$needs_offset" = true ]; then
        VSCODE_OFFSET_ENABLED=true
        # 默认偏移量，用户可以通过环境变量自定义
        OUTPUT_PREFIX="${SAGE_VSCODE_OFFSET:-    }"  # 默认4个空格
    fi
}

# 设置自定义偏移量
set_custom_offset() {
    local offset="$1"
    if [ -n "$offset" ]; then
        OUTPUT_PREFIX="$offset"
        VSCODE_OFFSET_ENABLED=true
    fi
}

# 禁用偏移
disable_offset() {
    OUTPUT_PREFIX=""
    VSCODE_OFFSET_ENABLED=false
}

# 启用偏移
enable_offset() {
    VSCODE_OFFSET_ENABLED=true
    OUTPUT_PREFIX="${SAGE_VSCODE_OFFSET:-    }"
}

# 格式化输出函数
format_output() {
    local text="$1"
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        echo -e "${OUTPUT_PREFIX}${text}"
    else
        echo -e "$text"
    fi
}

# 格式化 printf 输出
format_printf() {
    local format="$1"
    shift
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        printf "${OUTPUT_PREFIX}${format}" "$@"
    else
        printf "${format}" "$@"
    fi
}

# 重新定义常用的输出函数以支持偏移
# 这些函数会替代直接使用 echo -e
output_info() {
    format_output "${INFO} $1"
}

output_check() {
    format_output "${CHECK} $1"
}

output_warning() {
    format_output "${WARNING} $1"
}

output_error() {
    format_output "${CROSS} $1"
}

output_dim() {
    format_output "${DIM}$1${NC}"
}

output_success() {
    format_output "${SUCCESS} $1"
}

# 特殊的居中文本函数（考虑偏移）
center_text_formatted() {
    local text="$1"
    local color="${2:-$NC}"
    
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        # 如果启用了偏移，需要调整居中计算
        local prefix_length=${#OUTPUT_PREFIX}
        local width=$(($(get_terminal_width) - prefix_length))
        local text_len=$(text_length "$text")
        
        if [ "$text_len" -ge "$width" ]; then
            format_printf "%b%s%b\n" "$color" "$text" "$NC"
            return
        fi
        
        local padding=$(( (width - text_len) / 2 ))
        [ "$padding" -lt 0 ] && padding=0
        
        local spaces=""
        for (( i=0; i<padding; i++ )); do
            spaces+=" "
        done
        
        format_printf "%s%b%s%b\n" "$spaces" "$color" "$text" "$NC"
    else
        # 使用原始的居中函数
        center_text "$text" "$color"
    fi
}

# 带额外偏移的居中文本函数（用于特殊字符修正）
center_text_with_extra_offset() {
    local text="$1"
    local color="${2:-$NC}"
    local extra_offset="${3:-0}"
    
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        local prefix_length=${#OUTPUT_PREFIX}
        local width=$(($(get_terminal_width) - prefix_length))
        local text_len=$(text_length "$text")
        
        if [ "$text_len" -ge "$width" ]; then
            format_printf "%b%s%b\n" "$color" "$text" "$NC"
            return
        fi
        
        # 加上额外偏移
        local padding=$(( (width - text_len) / 2 + extra_offset ))
        [ "$padding" -lt 0 ] && padding=0
        
        local spaces=""
        for (( i=0; i<padding; i++ )); do
            spaces+=" "
        done
        
        format_printf "%s%b%s%b\n" "$spaces" "$color" "$text" "$NC"
    else
        # 不启用偏移时，使用原始的居中函数
        center_text "$text" "$color"
    fi
}

# 特殊的分隔线函数（考虑偏移）
draw_line_formatted() {
    local char="${1:-═}"
    local color="${2:-$BLUE}"

    draw_line "$char" "$color"
}

# 显示偏移状态（调试用）
show_offset_status() {
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        echo "🔧 VS Code 偏移已启用，前缀: '${OUTPUT_PREFIX}' (长度: ${#OUTPUT_PREFIX})"
    else
        echo "🔧 VS Code 偏移已禁用"
    fi
}

# ================================================================
# 图标偏移处理函数
# ================================================================

# 格式化图标输出，支持前后空格偏移
# 参数：
#   $1: 图标 (如 ⚙️ ✅ ❌ ⚠️ 等)
#   $2: 文本内容
#   $3: 前置空格数量 (可选，默认根据环境自动调整)
#   $4: 后置空格数量 (可选，默认1个空格)
#   $5: 颜色代码 (可选)
format_icon_output() {
    local icon="$1"
    local text="$2"
    local pre_spaces="${3:-}"
    local post_spaces="${4:-}"
    local color="${5:-$NC}"
    
    # 如果没有指定前置空格，使用自动调整
    if [ -z "$pre_spaces" ]; then
        if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
            pre_spaces="${SAGE_ICON_PRE_OFFSET:-2}"  # 默认前置2个空格
        else
            pre_spaces="0"  # 非VS Code环境不添加前置空格
        fi
    fi
    
    # 如果没有指定后置空格，使用默认值
    if [ -z "$post_spaces" ]; then
        if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
            post_spaces="${SAGE_ICON_POST_OFFSET:-1}"  # 默认后置1个空格
        else
            post_spaces="1"  # 默认1个空格
        fi
    fi
    
    # 生成前置空格
    local pre_padding=""
    for (( i=0; i<pre_spaces; i++ )); do
        pre_padding+=" "
    done
    
    # 生成后置空格
    local post_padding=""
    for (( i=0; i<post_spaces; i++ )); do
        post_padding+=" "
    done
    
    # 输出格式化的图标和文本
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        echo -e "${OUTPUT_PREFIX}${pre_padding}${color}${icon}${post_padding}${text}${NC}"
    else
        echo -e "${pre_padding}${color}${icon}${post_padding}${text}${NC}"
    fi
}

# 快捷图标输出函数
output_icon_info() {
    format_icon_output "ℹ️" "$1" "" "" "$BLUE"
}

output_icon_success() {
    format_icon_output "✅" "$1" "" "" "$GREEN"
}

output_icon_warning() {
    format_icon_output "⚠️" "$1" "" "" "$YELLOW"
}

output_icon_error() {
    format_icon_output "❌" "$1" "" "" "$RED"
}

output_icon_gear() {
    format_icon_output "⚙️" "$1" "" "" "$CYAN"
}

output_icon_rocket() {
    format_icon_output "🚀" "$1" "" "" "$PURPLE"
}

output_icon_package() {
    format_icon_output "📦" "$1" "" "" "$BLUE"
}

output_icon_check() {
    format_icon_output "✔️" "$1" "" "" "$GREEN"
}

output_icon_cross() {
    format_icon_output "✖️" "$1" "" "" "$RED"
}

output_icon_sparkles() {
    format_icon_output "✨" "$1" "" "" "$YELLOW"
}

# 自定义图标输出（用户可以指定任意图标）
output_custom_icon() {
    local icon="$1"
    local text="$2"
    local pre_spaces="${3:-}"
    local post_spaces="${4:-}"
    local color="${5:-$NC}"
    
    format_icon_output "$icon" "$text" "$pre_spaces" "$post_spaces" "$color"
}

# 图标偏移配置函数
# 设置全局图标前置偏移量
set_icon_pre_offset() {
    local offset="$1"
    if [[ "$offset" =~ ^[0-9]+$ ]]; then
        export SAGE_ICON_PRE_OFFSET="$offset"
    else
        echo "错误: 偏移量必须是非负整数" >&2
        return 1
    fi
}

# 设置全局图标后置偏移量
set_icon_post_offset() {
    local offset="$1"
    if [[ "$offset" =~ ^[0-9]+$ ]]; then
        export SAGE_ICON_POST_OFFSET="$offset"
    else
        echo "错误: 偏移量必须是非负整数" >&2
        return 1
    fi
}

# 重置图标偏移设置为默认值
reset_icon_offset() {
    unset SAGE_ICON_PRE_OFFSET
    unset SAGE_ICON_POST_OFFSET
}

# 显示当前图标偏移配置
show_icon_offset_config() {
    echo "📐 图标偏移配置："
    echo "  前置偏移: ${SAGE_ICON_PRE_OFFSET:-2} 个空格"
    echo "  后置偏移: ${SAGE_ICON_POST_OFFSET:-1} 个空格"
    echo "  VS Code偏移: $([ "$VSCODE_OFFSET_ENABLED" = true ] && echo "启用" || echo "禁用")"
}

# 便捷的图标+文本输出函数
# 参数: icon text [前置空格数] [后置空格数]
echo_icon() {
    local icon="$1"
    local text="$2"
    local prefix_spaces="${3:-2}"
    local suffix_spaces="${4:-2}"
    
    # 使用已有的 format_icon_output 函数
    format_icon_output "$icon" "$text" "$prefix_spaces" "$suffix_spaces"
}
