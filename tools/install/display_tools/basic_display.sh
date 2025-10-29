#!/bin/bash
# SAGE 安装脚本 - 基础显示工具
# 包含文本格式化、终端操作等基础显示函数

# 导入颜色定义和输出格式化
source "$(dirname "${BASH_SOURCE[0]}")/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/output_formatter.sh"

# 获取终端宽度
get_terminal_width() {
    if command -v tput >/dev/null 2>&1; then
        tput cols 2>/dev/null || echo "80"
    else
        echo "80"
    fi
}

# 计算纯文本长度（去除 ANSI 转义序列）
text_length() {
    local text="$1"
    local clean_text=$(echo -e "$text" | sed 's/\x1b\[[0-9;]*m//g')
    echo ${#clean_text}
}

# 计算显示宽度（考虑 emoji 和中文字符的实际显示宽度）
display_width() {
    local text="$1"
    local clean_text=$(echo -e "$text" | sed 's/\x1b\[[0-9;]*m//g')

    # 使用 printf 和 wc 来计算实际显示宽度
    # 这个方法更准确地处理 emoji 和多字节字符
    printf "%s" "$clean_text" | wc -m
}

# 居中显示文本
center_text() {
    local text="$1"
    local color="${2:-$NC}"
    local width=$(get_terminal_width)
    local text_len=$(display_width "$text")

    if [ "$text_len" -ge "$width" ]; then
        printf "%b%s%b\n" "$color" "$text" "$NC"
        return
    fi

    local padding=$(( (width - text_len) / 2 ))
    [ "$padding" -lt 0 ] && padding=0

    local spaces=""
    for (( i=0; i<padding; i++ )); do
        spaces+=" "
    done

    printf "%s%b%s%b\n" "$spaces" "$color" "$text" "$NC"
}

# 计算与 SAGE LOGO 对齐的文本位置
# 目标是让文本的第一个字符与 LOGO 的 S 字母对齐
align_with_logo() {
    local text="$1"
    local color="${2:-$NC}"

    # LOGO 第一行（这里需要与 interface.sh 中的 LOGO 保持一致）
    local logo_line="   ███████╗ █████╗  ██████╗ ███████╗"
    local width=$(get_terminal_width)
    local logo_len=$(display_width "$logo_line")
    local logo_padding=$(( (width - logo_len) / 2 ))

    # S 字母位置 = LOGO左边距 + 3个空格 + 1（因为我们要对齐S的位置）
    local s_position=$((logo_padding + 3))

    # 让文本的第一个字符（🚀）与 S 对齐
    local spaces=""
    for (( i=0; i<s_position; i++ )); do
        spaces+=" "
    done

    printf "%s%b%s%b\n" "$spaces" "$color" "$text" "$NC"
}

# 绘制分隔线
draw_line() {
    local char="${1:-═}"
    local color="${2:-$BLUE}"
    local width=$(get_terminal_width)

    local line=""
    for (( i=0; i<width; i++ )); do
        line+="$char"
    done
    printf "%b%s%b\n" "$color" "$line" "$NC"
}

# 安装进度动画
show_spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}
