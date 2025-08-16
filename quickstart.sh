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

# 打字机效果
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

# 左对齐输出（替代居中）
align_left() {
    local text="$1"
    local color="${2:-$NC}"
    printf "%b%s%b\n" "$color" "$text" "$NC"
}

# 绘制分隔线（改为简单左对齐）
draw_line() {
    local char="${1:-═}"
    local color="${2:-$BLUE}"
    printf "%b" "$color"
    printf "%s\n" "$(printf "%0.s$char" $(seq 1 60))"
    printf "%b" "$NC"
}

# 绘制装饰性边框（左对齐）
draw_border() {
    local text="$1"
    local padding=2
    local text_length=${#text}
    local border_width=$((text_length + padding * 2))
    printf "%b\n" "$CYAN╔$(printf "%0.s═" $(seq 1 $border_width))╗$NC"
    printf "%b\n" "$CYAN║$(printf "%*s" $padding "")$text$(printf "%*s" $padding "")║$NC"
    printf "%b\n" "$CYAN╚$(printf "%0.s═" $(seq 1 $border_width))╝$NC"
}

print_info() {
    printf "%b\n" "${GREEN}ℹ️ $1${NC}"
}

print_warning() {
    printf "%b\n" "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    printf "%b\n" "${RED}❌ $1${NC}"
}

progress_bar() {
    local task="$1"
    local cmd="$2"
    printf "%b" "${BLUE}${task}...${NC} "
    for i in {1..20}; do
        printf "▓"
        sleep 0.05
    done
    printf "  "
    if eval "$cmd" &>/dev/null; then
        printf "%b\n" "${GREEN}✔${NC}"
    else
        printf "%b\n" "${RED}✘${NC}"
        return 1
    fi
}

# 检查Python是否可用
check_python() {
    progress_bar "检查 Python3" "command -v python3"
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
        print_info "Python 版本: $python_version ✓"
    else
        print_error "Python版本 $python_version 不满足要求，需要 3.11"
        exit 1
    fi
}

# 检查模块化安装系统
check_modular_installer() {
    INSTALLER_PATH="$PROJECT_ROOT/tools/install/install.py"
    progress_bar "检查安装器" "[[ -f \"$INSTALLER_PATH\" ]]"
    print_info "找到模块化安装系统: $INSTALLER_PATH"
}

# 显示欢迎信息
show_welcome() {
    clear
    echo ""
    draw_line
    align_left "🚀 欢迎使用 SAGE 快速启动脚本"
    draw_line
    echo ""
}

# 主函数
main() {
    show_welcome
    check_python
    check_modular_installer
    if [[ $# -eq 0 ]]; then
        echo ""
        align_left "🤔 如何继续？"
        cat <<EOF

  1) 交互式安装 (推荐新用户)
  2) 开发模式安装  
  3) 最小安装
  4) 显示所有安装模式
  5) 查看使用方法
  6) 退出

EOF
        read -p "请选择 (1-6): " choice
        case $choice in
            1) print_info "启动交互式安装..."; exec python3 "$PROJECT_ROOT/tools/install/install.py" ;;
            2) print_info "启动开发模式安装..."; exec python3 "$PROJECT_ROOT/tools/install/install.py" --dev ;;
            3) print_info "启动最小安装..."; exec python3 "$PROJECT_ROOT/tools/install/install.py" --minimal ;;
            4) exec python3 "$PROJECT_ROOT/tools/install/install.py" --list-profiles ;;
            5) cat <<EOF
💡 使用方法:

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
            6) print_info "退出安装"; exit 0 ;;
            *) print_warning "无效选择，启动交互式安装..."; exec python3 "$PROJECT_ROOT/tools/install/install.py" ;;
        esac
    else
        print_info "委托给模块化安装系统..."
        exec python3 "$PROJECT_ROOT/tools/install/install.py" "$@"
    fi
}

trap 'print_error "安装过程中断"; exit 1' INT TERM

main "$@"
