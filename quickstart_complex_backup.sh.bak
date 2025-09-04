#!/bin/bash

# 强制告诉 VS Code/xterm.js 支持 ANSI 和 256 色
export TERM=xterm-256color
set -e

# 获取脚本所在目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色和样式定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[1;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Unicode 符号
ROCKET="🚀"
GEAR="⚙️"
CHECK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
SPARKLES="✨"
THINKING="🤔"
BOOK="📚"
TARGET="🎯"
RUNNER="🏃"
WRENCH="🔧"

# 加载动画字符
SPINNER_CHARS=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')

# 获取实际终端宽度的函数（兼容 VS Code 远程终端）
get_terminal_width() {
    # 尝试多种方法获取终端宽度
    local width
    
    # 方法1: tput（最可靠）
    if command -v tput >/dev/null 2>&1; then
        width=$(tput cols 2>/dev/null)
        if [[ "$width" =~ ^[0-9]+$ ]] && [ "$width" -gt 20 ] && [ "$width" -lt 300 ]; then
            echo "$width"
            return
        fi
    fi
    
    # 方法2: stty
    if command -v stty >/dev/null 2>&1; then
        width=$(stty size 2>/dev/null | cut -d' ' -f2)
        if [[ "$width" =~ ^[0-9]+$ ]] && [ "$width" -gt 20 ] && [ "$width" -lt 300 ]; then
            echo "$width"
            return
        fi
    fi
    
    # 方法3: COLUMNS 环境变量
    if [[ -n "$COLUMNS" ]] && [[ "$COLUMNS" =~ ^[0-9]+$ ]]; then
        echo "$COLUMNS"
        return
    fi
    
    # 默认宽度（VS Code 远程终端通常是这个宽度）
    echo "80"
}

# 计算纯文本长度（去除 ANSI 转义序列和 Unicode 字符的影响）
text_length() {
    local text="$1"
    # 去除 ANSI 转义序列
    local clean_text=$(echo -e "$text" | sed 's/\x1b\[[0-9;]*m//g')
    # 对于包含 Unicode 字符的文本，使用更保守的计算方法
    if echo "$clean_text" | grep -q '[^\x00-\x7F]'; then
        # 包含 Unicode 字符，使用字符数而不是字节数
        echo "$clean_text" | wc -m
    else
        # 纯 ASCII，使用字符数
        echo ${#clean_text}
    fi
}

# 上下左右完全居中显示文本
center_screen_text() {
    local text="$1"
    local color="${2:-$NC}"
    local width=$(get_terminal_width)

    # 计算终端高度
    local height
    if command -v tput >/dev/null 2>&1; then
        height=$(tput lines 2>/dev/null)
    elif command -v stty >/dev/null 2>&1; then
        height=$(stty size 2>/dev/null | cut -d' ' -f1)
    else
        height=24  # 默认高度
    fi

    # 文本行数（这里按单行处理）
    local text_len=$(text_length "$text")

    # 左右居中的空格
    local padding_x=$(( (width - text_len) / 2 ))
    [ "$padding_x" -lt 0 ] && padding_x=0
    local spaces=""
    for (( i=0; i<padding_x; i++ )); do
        spaces+=" "
    done

    # 上下居中的空行
    local padding_y=$(( height / 2 ))
    for (( i=0; i<padding_y; i++ )); do
        echo ""
    done

    # 输出文本
    printf "%s%b%s%b\n" "$spaces" "$color" "$text" "$NC"
}


# 改进的居中函数
center_text() {
    local text="$1"
    local color="${2:-$NC}"
    local extra_offset="${3:-0}"  # 新增额外偏移参数
    local width=$(get_terminal_width)
    local text_len=$(text_length "$text")
    
    # 如果文本长度超过终端宽度，直接左对齐输出
    if [ "$text_len" -ge "$width" ]; then
        printf "%b%s%b\n" "$color" "$text" "$NC"
        return
    fi
    
    # 计算左边距，加上额外偏移
    local padding=$(( (width - text_len) / 2 + extra_offset ))
    
    # 确保 padding 不为负数
    if [ "$padding" -lt 0 ]; then
        padding=0
    fi
    
    # 生成空格字符串
    local spaces=""
    for (( i=0; i<padding; i++ )); do
        spaces+=" "
    done
    
    printf "%s%b%s%b\n" "$spaces" "$color" "$text" "$NC"
}

# 多行文本居中函数（用于 LOGO）
center_multiline() {
    local color="${1:-$NC}"
    local width=$(get_terminal_width)
    
    while IFS= read -r line; do
        local text_len=$(text_length "$line")
        
        # 如果文本长度超过终端宽度，直接左对齐输出
        if [ "$text_len" -ge "$width" ]; then
            printf "%b%s%b\n" "$color" "$line" "$NC"
            continue
        fi
        
        # 计算左边距
        local padding=$(( (width - text_len) / 2))
        
        # 生成空格字符串
        local spaces=""
        for (( i=0; i<padding; i++ )); do
            spaces+=" "
        done
        
        printf "%s%b%s%b\n" "$spaces" "$color" "$line" "$NC"
    done
}

# 左对齐输出（作为备用选项）
align_left() {
    local text="$1"
    local color="${2:-$NC}"
    printf "%b%s%b\n" "$color" "$text" "$NC"
}

# 改进的分隔线绘制函数
draw_line() {
    local char="${1:-═}"
    local color="${2:-$BLUE}"
    local width=$(get_terminal_width)
    
    # 使用和 center_text 相同的宽度逻辑
    # 这样分隔线就会填满整个终端宽度
    local line=""
    for (( i=0; i<width; i++ )); do
        line+="$char"
    done
    
    center_text "$line" "$color"
}

# 改进的边框绘制函数
draw_border() {
    local text="$1"
    local color="${2:-$CYAN}"
    local padding=2
    local text_len=$(text_length "$text")
    local border_width=$((text_len + padding * 2))
    
    # 上边框
    printf "%b╔" "$color"
    for (( i=0; i<border_width; i++ )); do
        printf "═"
    done
    printf "╗%b\n" "$NC"
    
    # 中间内容
    printf "%b║" "$color"
    for (( i=0; i<padding; i++ )); do
        printf " "
    done
    printf "%s" "$text"
    for (( i=0; i<padding; i++ )); do
        printf " "
    done
    printf "║%b\n" "$NC"
    
    # 下边框
    printf "%b╚" "$color"
    for (( i=0; i<border_width; i++ )); do
        printf "═"
    done
    printf "╝%b\n" "$NC"
}

# 打字机效果（优化）
typewriter() {
    local text="$1"
    local delay="${2:-0.03}"
    local color="${3:-$WHITE}"
    printf "%b" "$color"
    for (( i=0; i<${#text}; i++ )); do
        printf "%s" "${text:$i:1}"
        sleep "$delay"
    done
    printf "%b\n" "$NC"
}

# 显示 SAGE LOGO
show_logo() {
    echo ""
    
    # SAGE LOGO (修正为正确的 SAGE)
    local logo_lines=(
        "   ███████╗ █████╗  ██████╗ ███████╗"
        "   ██╔════╝██╔══██╗██╔════╝ ██╔════╝"
        "   ███████╗███████║██║  ███╗█████╗  "
        "   ╚════██║██╔══██║██║   ██║██╔══╝  "
        "   ███████║██║  ██║╚██████╔╝███████╗"
        "   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
    )
    
    # 计算第一行的居中位置
    local width=$(get_terminal_width)
    local first_line_len=$(text_length "${logo_lines[0]}")
    local padding=0
    
    if [ "$first_line_len" -lt "$width" ]; then
        padding=$(( (width - first_line_len) / 2 ))
    fi
    
    # 生成左边距字符串
    local spaces=""
    for (( i=0; i<padding; i++ )); do
        spaces+=" "
    done
    
    # 输出所有 LOGO 行，使用相同的左边距
    for line in "${logo_lines[@]}"; do
        printf "%s%b%s%b\n" "$spaces" "$CYAN$BOLD" "$line" "$NC"
    done
    
    echo ""
    center_text "https://intellistream.github.io/SAGE-Pub/" "$GRAY"
    center_text "intellistream 2025" "$GRAY"
}

# 新的检查输出函数 - 左对齐
print_check_info() {
    printf "%b✅  %s%b\n" "$GREEN" "$1" "$NC"
}

print_check_detail() {
    printf "%bℹ️   %s%b\n" "$BLUE" "$1" "$NC"
}

print_check_error() {
    printf "%b❌  %s%b\n" "$RED" "$1" "$NC"
}

print_check_warning() {
    printf "%b⚠️  %s%b\n" "$YELLOW" "$1" "$NC"
}

# 带动态加载动画的检查函数
check_with_spinner() {
    local check_name="$1"
    local check_cmd="$2"
    
    # 显示检查开始状态
    printf "%b🔧  %b正在检查 %s ...%b" "$BLUE" "$NC" "$check_name" "$NC"
    
    # 启动后台任务执行检查
    local temp_file=$(mktemp)
    (eval "$check_cmd" > "$temp_file" 2>&1; echo $? >> "$temp_file") &
    local bg_pid=$!
    
    # 显示加载动画
    local spinner_index=0
    while kill -0 $bg_pid 2>/dev/null; do
        printf "\r%b🔧  %s 正在检查 %s ...%b" "$BLUE" "${SPINNER_CHARS[$spinner_index]}" "$check_name" "$NC"
        spinner_index=$(((spinner_index + 1) % ${#SPINNER_CHARS[@]}))
        sleep 0.1
    done
    
    # 等待后台任务完成
    wait $bg_pid
    
    # 读取结果
    local output=$(head -n -1 "$temp_file")
    local exit_code=$(tail -n 1 "$temp_file")
    rm "$temp_file"
    
    # 清除当前行并显示最终结果
    printf "\r%b🔧  %s 正在检查 %s ...%b\n" "$BLUE" "${SPINNER_CHARS[$((spinner_index-1))]}" "$check_name" "$NC"
    
    if [ "$exit_code" -eq 0 ]; then
        print_check_info "$check_name 检查完成"
        if [ -n "$output" ]; then
            while IFS= read -r line; do
                [ -n "$line" ] && print_check_detail "$line"
            done <<< "$output"
        fi
        return 0
    else
        print_check_error "$check_name 检查失败"
        if [ -n "$output" ]; then
            while IFS= read -r line; do
                [ -n "$line" ] && print_check_detail "$line"
            done <<< "$output"
        fi
        return 1
    fi
}
# 系统信息检查
check_system() {
    local check_name="系统版本"
    printf "%b🔧  正在检查 %s ...%b" "$BLUE" "$check_name" "$NC"

    # 直接执行检查命令，不放入后台
    local output
    local exit_code=0
    output=$(eval '
        # 获取系统信息
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v lsb_release >/dev/null 2>&1; then
                SYSTEM_NAME=$(lsb_release -si 2>/dev/null)
                SYSTEM_VERSION=$(lsb_release -sr 2>/dev/null)
            elif [ -f /etc/os-release ]; then
                source /etc/os-release
                SYSTEM_NAME="$NAME"
                SYSTEM_VERSION="$VERSION_ID"
            else
                SYSTEM_NAME="Linux"
                SYSTEM_VERSION="Unknown"
            fi
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            SYSTEM_NAME="macOS"
            SYSTEM_VERSION=$(sw_vers -productVersion 2>/dev/null)
        else
            SYSTEM_NAME="$OSTYPE"
            SYSTEM_VERSION="Unknown"
        fi
        
        # 获取CPU架构
        ARCH=$(uname -m 2>/dev/null)
        
        echo "操作系统: $SYSTEM_NAME $SYSTEM_VERSION    CPU 架构: $ARCH"
    ' 2>&1) || exit_code=$? # 捕获命令输出和退出码

    # 根据结果打印信息
    printf "\r" # 回到行首，覆盖 "正在检查..."
    if [ "$exit_code" -eq 0 ]; then
        print_check_info "$check_name 检查完成"
        if [ -n "$output" ]; then
            while IFS= read -r line; do
                [ -n "$line" ] && print_check_detail "$line"
            done <<< "$output"
        fi
        return 0
    else
        print_check_error "$check_name 检查失败"
        if [ -n "$output" ]; then
            while IFS= read -r line; do
                [ -n "$line" ] && print_check_detail "$line"
            done <<< "$output"
        fi
        return 1
    fi
}

# Python检查
check_python() {
    local check_cmd='
        # 检查Python3是否存在
        if ! command -v python3 >/dev/null 2>&1; then
            echo "Python3 未找到"
            exit 1
        fi
        
        # 获取Python信息
        PYTHON_PATH=$(which python3)
        PYTHON_VERSION=$(python3 -c "import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\")")
        
        # 检查版本要求
        if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            echo "Python版本: $PYTHON_VERSION (不满足要求，需要 3.11+)"
            echo "Python路径: $PYTHON_PATH"
            exit 1
        fi
        
        echo "Python版本: $PYTHON_VERSION ($PYTHON_PATH)"
    '
    
    check_with_spinner "Python" "$check_cmd"
}

# Conda检查
check_conda() {
    local check_cmd='
        # 检查conda是否存在
        if ! command -v conda >/dev/null 2>&1; then
            echo "Conda 未安装或未在PATH中"
            exit 1
        fi
        
        # 获取Conda信息
        CONDA_PATH=$(which conda)
        CONDA_VERSION=$(conda --version 2>/dev/null | cut -d" " -f2)
        
        echo "Conda版本: $CONDA_VERSION ($CONDA_PATH)"
    '
    
    check_with_spinner "Conda" "$check_cmd"
}

# 模块化安装器检查
check_modular_installer() {
    local installer_path="$PROJECT_ROOT/tools/install/install.py"
    local check_cmd="
        if [[ -f \"$installer_path\" ]]; then
            echo \"文件位置: $installer_path\"
        else
            echo \"安装器文件不存在: $installer_path\"
            exit 1
        fi
    "
    
    check_with_spinner "模块化安装器" "$check_cmd"
}

# 统一的输出函数（保持兼容性）
print_info() {
    local text="ℹ️  $1"
    center_text "$text" "$GREEN" 5
}

print_warning() {
    local text="⚠️  $1"
    center_text "$text" "$YELLOW" 5
}

print_error() {
    printf "%b❌ %s%b\n" "$RED" "$1" "$NC"
}

print_success() {
    local text="✅ $1"
    center_text "$text" "$GREEN" 5
}

print_step() {
    local text="🔧 $1"
    center_text "$text" "$BLUE" 5
}

# 显示欢迎信息
show_welcome() {
    clear
    echo ""
    draw_line
    center_text "🚀 欢迎使用 SAGE 快速部署脚本" "$BOLD$WHITE"
    draw_line
    show_logo
    draw_line
}

# 执行所有检查
run_all_checks() {
    echo ""
    echo "开始依赖检查："
    echo ""
    
    # 执行所有检查
    check_system
    echo ""
    
    check_python || { print_error "Python检查失败，安装终止"; exit 1; }
    echo ""
    
    # Conda检查失败不会终止程序，只是警告
    if ! check_conda; then
        print_check_warning "Conda 未找到，将尝试使用系统 Python 环境"
    fi
    echo ""
    
    check_modular_installer || { print_error "模块化安装器检查失败，安装终止"; exit 1; }
    echo ""
    
    echo "所有检查完成！"
    draw_line
}

# 主函数
main() {
    show_welcome
    run_all_checks
    
    if [[ $# -eq 0 ]]; then
        echo ""
        printf "%b😊 请选择【安装方式】以继续您的安装：%b\n" "$WHITE" "$NC"
        printf "\n"
        printf "  %b1) 交互式安装 (推荐新用户)%b\n" "$GREEN" "$NC"
        printf "  2) 开发模式安装\n"
        printf "  3) 最小安装\n"
        printf "  %b4) 显示所有安装模式%b\n" "$BLUE" "$NC"
        printf "  %b5) 查看使用方法%b\n" "$BLUE" "$NC"
        printf "  %b6) 退出%b\n" "$RED" "$NC"
        printf "\n"
        read -p "请选择 (1-6): " choice
        case $choice in
            1) clear
               center_screen_text "ℹ️  启动交互式安装中..." "$GREEN"
               sleep 1
               exec python3 "$PROJECT_ROOT/tools/install/install.py" ;;
            2) clear
               center_screen_text "ℹ️  启动开发模式安装中..." "$GREEN"
               sleep 1
               exec python3 "$PROJECT_ROOT/tools/install/install.py" --dev ;;
            3) clear
               center_screen_text "ℹ️  启动最小安装中..." "$GREEN"
               sleep 1
               exec python3 "$PROJECT_ROOT/tools/install/install.py" --minimal ;;
            4) python3 "$PROJECT_ROOT/tools/install/install.py" --list-profiles
               echo ""
               clear
               main "$@" ;;
            5) center_text "💡 使用方法:" "$CYAN" 4
               cat <<EOF

  🏃 快速开始:
    ./quickstart.sh                       # 交互式安装（推荐新用户）
    ./quickstart.sh --dev                 # 开发模式
    ./quickstart.sh --minimal             # 最小安装

  🎯 高级选项:
    ./quickstart.sh --profile standard    # 标准安装
    ./quickstart.sh --env-name my-sage    # 自定义环境名
    ./quickstart.sh --quiet               # 静默模式
    ./quickstart.sh --force               # 强制重装

  📋 查看选项:
    ./quickstart.sh --list-profiles       # 查看所有安装模式
    ./quickstart.sh --help                # 详细帮助
    
  🔧 直接使用模块化系统:
    python3 tools/install/install.py --help

EOF
                exit 0 ;;
            6) printf "%b您已成功退出安装程序%b\n" "$RED" "$NC"; exit 0 ;;
            *) print_warning "无效选择，启动交互式安装..."; exec python3 "$PROJECT_ROOT/tools/install/install.py" ;;
        esac
    else
        print_info "委托给模块化安装系统..."
        exec python3 "$PROJECT_ROOT/tools/install/install.py" "$@"
    fi
}

trap 'printf "%b❌ 安装过程中断%b\n" "$RED" "$NC"; exit 1' INT TERM

main "$@"