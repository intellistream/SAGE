#!/bin/bash
# 🚀 SAGE 快速安装脚本 - 保留漂亮界面，简化安装逻辑

# 强制告诉 VS Code/xterm.js 支持 ANSI 和 256 色
export TERM=xterm-256color
set -e

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

# 居中显示文本
center_text() {
    local text="$1"
    local color="${2:-$NC}"
    local width=$(get_terminal_width)
    local text_len=$(text_length "$text")
    
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

# 显示 SAGE LOGO
show_logo() {
    echo ""
    
    local logo_lines=(
        "   ███████╗ █████╗  ██████╗ ███████╗"
        "   ██╔════╝██╔══██╗██╔════╝ ██╔════╝"
        "   ███████╗███████║██║  ███╗█████╗  "
        "   ╚════██║██╔══██║██║   ██║██╔══╝  "
        "   ███████║██║  ██║╚██████╔╝███████╗"
        "   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
    )
    
    local width=$(get_terminal_width)
    local first_line_len=$(text_length "${logo_lines[0]}")
    local padding=0
    
    if [ "$first_line_len" -lt "$width" ]; then
        padding=$(( (width - first_line_len) / 2 ))
    fi
    
    local spaces=""
    for (( i=0; i<padding; i++ )); do
        spaces+=" "
    done
    
    for line in "${logo_lines[@]}"; do
        printf "%s%b%s%b\n" "$spaces" "$CYAN$BOLD" "$line" "$NC"
    done
    
    echo ""
    center_text "https://intellistream.github.io/SAGE-Pub/" "$GRAY"
    center_text "intellistream 2025" "$GRAY"
}

# 显示欢迎界面
show_welcome() {
    clear
    echo ""
    draw_line
    center_text "${ROCKET} 欢迎使用 SAGE 快速部署脚本" "$BOLD$WHITE"
    draw_line
    show_logo
    draw_line
}

# 检查是否已安装SAGE
check_existing_sage() {
    echo -e "${INFO} 检查是否已安装 SAGE..."
    
    # 检查是否能导入sage
    if python3 -c "import sage" 2>/dev/null; then
        local sage_version=$(python3 -c "import sage; print(sage.__version__)" 2>/dev/null || echo "unknown")
        echo -e "${WARNING} 检测到已安装的 SAGE v${sage_version}"
        return 0
    fi
    
    # 检查pip包列表
    local installed_packages=$(pip list 2>/dev/null | grep -E '^sage(-|$)' || echo "")
    if [ -n "$installed_packages" ]; then
        echo -e "${WARNING} 检测到已安装的 SAGE 相关包："
        echo -e "${DIM}$installed_packages${NC}"
        return 0
    fi
    
    return 1
}

# 卸载现有SAGE
uninstall_sage() {
    echo -e "${INFO} 卸载现有 SAGE 安装..."
    
    # 卸载所有SAGE相关包
    local sage_packages=(
        "sage"
        "sage-libs" 
        "sage-middleware"
        "sage-kernel"
        "sage-common"
    )
    
    for package in "${sage_packages[@]}"; do
        if pip show "$package" >/dev/null 2>&1; then
            echo -e "${DIM}  → 卸载 $package${NC}"
            if ! $PIP_CMD uninstall "$package" -y --quiet 2>/dev/null; then
                echo -e "${WARNING} 卸载 $package 时出现警告，继续..."
            fi
        fi
    done
    
    # 清理可能的开发模式安装
    echo -e "${DIM}  → 清理开发模式链接${NC}"
    for package in "${sage_packages[@]}"; do
        local package_path="packages/$package"
        if [ -d "$package_path" ]; then
            if $PIP_CMD uninstall "$package" -y --quiet 2>/dev/null; then
                echo -e "${DIM}    清理 $package 开发链接${NC}"
            fi
        fi
    done
    
    echo -e "${CHECK} SAGE 卸载完成"
}

# 询问是否卸载现有SAGE
ask_uninstall_sage() {
    echo ""
    echo -e "${BOLD}${YELLOW}⚠️  发现已安装的 SAGE${NC}"
    echo ""
    echo -e "${BLUE}为了确保安装的完整性，建议先卸载现有版本。${NC}"
    echo ""
    echo -e "${BLUE}选项：${NC}"
    echo -e "  [1] 卸载现有版本，然后安装新版本 (推荐)"
    echo -e "  [2] 跳过卸载，直接覆盖安装"
    echo -e "  [3] 取消安装"
    echo ""
    
    while true; do
        echo -ne "${BLUE}请选择 [1-3]: ${NC}"
        read -r choice
        case $choice in
            1)
                echo -e "${INFO} 将先卸载现有 SAGE，然后安装新版本"
                uninstall_sage
                return 0
                ;;
            2)
                echo -e "${WARNING} 跳过卸载，直接进行覆盖安装"
                echo -e "${DIM}注意：这可能导致版本冲突或安装问题${NC}"
                return 0
                ;;
            3)
                echo -e "${INFO} 用户取消安装"
                exit 0
                ;;
            *)
                echo -e "${WARNING} 无效选择，请输入 1-3"
                ;;
        esac
    done
}

# 系统检查函数
check_python() {
    echo -e "${INFO} 检查 Python 环境..."
    if ! command -v python3 &> /dev/null; then
        echo -e "${CROSS} Python3 未找到！请先安装 Python 3.8+"
        return 1
    fi
    
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${CHECK} Python 版本: $python_version"
    return 0
}

check_conda() {
    echo -e "${INFO} 检查 Conda 环境..."
    if ! command -v conda &> /dev/null; then
        echo -e "${WARNING} Conda 未找到，将使用系统 Python 环境"
        echo -e "${DIM}建议安装 Anaconda 或 Miniconda 获得更好的包管理体验${NC}"
        return 1
    fi
    
    local conda_version=$(conda --version 2>&1 | cut -d' ' -f2)
    echo -e "${CHECK} Conda 版本: $conda_version"
    
    # 检查当前环境
    local current_env=$(conda env list | grep '\*' | awk '{print $1}')
    echo -e "${INFO} 当前 Conda 环境: $current_env"
    
    return 0
}

# 询问用户是否创建新的 conda 环境
ask_conda_environment() {
    if ! command -v conda &> /dev/null; then
        return 1  # conda 不可用，跳过
    fi
    
    echo ""
    echo -e "${GEAR} ${BOLD}Conda 环境设置${NC}"
    echo ""
    echo -e "${BLUE}检测到 Conda 已安装，建议为 SAGE 创建独立环境${NC}"
    echo ""
    echo -e "选项："
    echo -e "  ${GREEN}[1] 创建新的 SAGE 环境 (推荐)${NC}"
    echo -e "  [2] 使用当前环境"
    echo -e "  [3] 手动指定环境名"
    echo ""
    
    while true; do
        echo -ne "${BLUE}请选择 [1-3]: ${NC}"
        read -r conda_choice
        case $conda_choice in
            1)
                SAGE_ENV_NAME="sage"
                create_conda_environment "$SAGE_ENV_NAME"
                break
                ;;
            2)
                echo -e "${INFO} 将在当前环境中安装 SAGE"
                SAGE_ENV_NAME=""
                break
                ;;
            3)
                echo -ne "${BLUE}请输入环境名称: ${NC}"
                read -r custom_env_name
                if [[ -n "$custom_env_name" ]]; then
                    SAGE_ENV_NAME="$custom_env_name"
                    create_conda_environment "$SAGE_ENV_NAME"
                    break
                else
                    echo -e "${WARNING} 环境名不能为空"
                fi
                ;;
            *)
                echo -e "${WARNING} 无效选择，请输入 1-3"
                ;;
        esac
    done
}

# 创建 conda 环境
create_conda_environment() {
    local env_name="$1"
    
    echo -e "${INFO} 创建 Conda 环境: $env_name"
    
    # 检查环境是否已存在
    if conda env list | grep -q "^$env_name "; then
        echo -e "${WARNING} 环境 '$env_name' 已存在"
        echo -ne "${BLUE}是否删除并重新创建? [y/N]: ${NC}"
        read -r recreate
        case "$recreate" in
            [yY]|[yY][eE][sS])
                echo -e "${INFO} 删除现有环境..."
                conda env remove -n "$env_name" -y &>/dev/null || true
                ;;
            *)
                echo -e "${INFO} 将在现有环境中安装"
                activate_conda_environment "$env_name"
                return 0
                ;;
        esac
    fi
    
    # 创建环境
    echo -e "${INFO} 创建新环境 '$env_name' (Python 3.11)..."
    if conda create -n "$env_name" python=3.11 -y &>/dev/null; then
        echo -e "${CHECK} 环境创建成功"
        activate_conda_environment "$env_name"
    else
        echo -e "${CROSS} 环境创建失败，将使用当前环境"
        SAGE_ENV_NAME=""
    fi
}

# 激活 conda 环境
activate_conda_environment() {
    local env_name="$1"
    
    echo -e "${INFO} 激活环境: $env_name"
    
    # 设置环境变量，让子进程使用正确的 conda 环境
    export CONDA_DEFAULT_ENV="$env_name"
    
    # 更新 pip 命令以使用指定环境
    PIP_CMD="conda run -n $env_name pip"
    PYTHON_CMD="conda run -n $env_name python"
    
    echo -e "${CHECK} 环境已激活"
    echo -e "${DIM}提示: 安装完成后运行 'conda activate $env_name' 来使用 SAGE${NC}"
}

check_pip() {
    echo -e "${INFO} 检查 pip..."
    
    local pip_cmd="python3 -m pip"
    if [[ -n "${PIP_CMD:-}" ]]; then
        pip_cmd="$PIP_CMD"
    fi
    
    if ! $pip_cmd --version &> /dev/null; then
        echo -e "${CROSS} pip 未找到！请先安装 pip"
        return 1
    fi
    echo -e "${CHECK} pip 可用"
    return 0
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

# 主安装函数
install_sage() {
    local mode="${1:-standard}"
    
    echo ""
    echo -e "${GEAR} 开始安装 SAGE 包 (${mode} 模式)..."
    echo ""
    
    # 检查是否已安装SAGE
    if check_existing_sage; then
        ask_uninstall_sage
    fi
    
    # 检查系统环境
    if ! check_python; then
        echo -e "${CROSS} Python 环境检查失败，安装终止"
        exit 1
    fi
    
    # 检查 conda 并询问环境设置
    if [ "${SAGE_USE_CONDA:-}" = "true" ]; then
        # 强制使用 conda
        if ! check_conda; then
            echo -e "${CROSS} conda 不可用，但已指定 --conda 选项"
            exit 1
        fi
        ask_conda_environment
    elif [ "${SAGE_USE_CONDA:-}" = "false" ]; then
        # 强制使用 pip
        echo -e "${INFO} 使用 pip 安装模式"
    else
        # 自动检测或询问用户
        if check_conda; then
            ask_conda_environment
        fi
    fi
    
    # 设置默认命令（如果没有设置 conda 环境）
    PIP_CMD="${PIP_CMD:-python3 -m pip}"
    PYTHON_CMD="${PYTHON_CMD:-python3}"
    
    if ! check_pip; then
        echo -e "${CROSS} pip 检查失败，安装终止"
        exit 1
    fi
    
    echo ""
    case "$mode" in
        "minimal")
            echo -e "${BLUE}最小安装模式：仅安装核心 SAGE 包${NC}"
            install_core_packages
            ;;
        "standard")
            echo -e "${BLUE}标准安装模式：核心包 + 科学计算库${NC}"
            echo -e "${DIM}包含: numpy, pandas, matplotlib, scipy, jupyter${NC}"
            install_core_packages
            install_scientific_packages
            ;;
        "dev")
            echo -e "${BLUE}开发者安装模式：标准包 + 开发工具${NC}"
            echo -e "${DIM}包含: 标准安装 + pytest, black, mypy, pre-commit${NC}"
            install_core_packages
            install_scientific_packages
            install_dev_packages
            ;;
        *)
            echo -e "${WARNING} 未知安装模式: $mode，使用标准模式"
            install_core_packages
            install_scientific_packages
            ;;
    esac
    
    echo ""
    echo -e "${CHECK} SAGE 安装完成！"
    
    # 显示安装信息
    show_install_success "$mode"
}

# 安装核心包
install_core_packages() {
    echo -e "${INFO} 安装核心 SAGE 包..."
    
    # SAGE 包安装顺序：sage-common → sage-kernel → sage-middleware → sage-libs → sage
    local sage_packages=("sage-common" "sage-kernel" "sage-middleware" "sage-libs" "sage")
    
    for package in "${sage_packages[@]}"; do
        local package_path="packages/$package"
        
        if [ -d "$package_path" ]; then
            echo -e "${DIM}  → 安装 $package (开发模式)${NC}"
            if $PIP_CMD install -e "$package_path" --quiet; then
                echo -e "${CHECK} $package 安装成功"
            else
                echo -e "${CROSS} $package 安装失败！"
                exit 1
            fi
        else
            echo -e "${WARNING} 跳过不存在的包: $package"
        fi
    done
    
    echo -e "${CHECK} SAGE 核心包安装成功！"
    return 0
}

# 安装科学计算包
install_scientific_packages() {
    echo -e "${INFO} 安装科学计算库..."
    local packages=(
        "numpy>=1.21.0"
        "pandas>=1.3.0" 
        "matplotlib>=3.4.0"
        "scipy>=1.7.0"
        "jupyter>=1.0.0"
        "ipykernel>=6.0.0"
    )
    
    for package in "${packages[@]}"; do
        echo -e "${DIM}  → 安装 $package${NC}"
        if $PIP_CMD install "$package" --quiet; then
            echo -e "${CHECK} $package 安装成功"
        else
            echo -e "${WARNING} $package 安装可能失败，继续..."
        fi
    done
}

# 安装开发包
install_dev_packages() {
    echo -e "${INFO} 安装开发工具..."
    local dev_packages=(
        "pytest>=6.0.0"
        "pytest-cov>=2.12.0"
        "black>=21.0.0"
        "flake8>=3.9.0"
        "mypy>=0.910"
        "pre-commit>=2.15.0"
    )
    
    for package in "${dev_packages[@]}"; do
        echo -e "${DIM}  → 安装 $package${NC}"
        if $PIP_CMD install "$package" --quiet; then
            echo -e "${CHECK} $package 安装成功"
        else
            echo -e "${WARNING} $package 安装可能失败，继续..."
        fi
    done
}

# 显示安装成功信息
show_install_success() {
    local mode="$1"
    
    echo ""
    echo -e "${BOLD}${GREEN}🎉 SAGE 安装成功！${NC}"
    echo ""
    
    # 显示已安装的内容
    case "$mode" in
        "minimal")
            echo -e "${BLUE}已安装 (最小模式):${NC}"
            echo -e "  ${CHECK} SAGE 核心包"
            ;;
        "standard")
            echo -e "${BLUE}已安装 (标准模式):${NC}"
            echo -e "  ${CHECK} SAGE 核心包"
            echo -e "  ${CHECK} 科学计算库 (numpy, pandas, matplotlib, scipy, jupyter)"
            ;;
        "dev")
            echo -e "${BLUE}已安装 (开发者模式):${NC}"
            echo -e "  ${CHECK} SAGE 核心包"
            echo -e "  ${CHECK} 科学计算库"
            echo -e "  ${CHECK} 开发工具 (pytest, black, mypy, pre-commit)"
            ;;
    esac
    
    echo ""
    echo -e "${BOLD}快速开始:${NC}"
    echo -e "  ${DIM}# 验证安装${NC}"
    echo -e "  python3 -c 'import sage; print(f\"SAGE v{sage.__version__} 安装成功！\")'"
    echo ""
    echo -e "  ${DIM}# 运行示例${NC}"
    echo -e "  cd examples && python3 rag/basic_rag.py"
    echo ""
    echo -e "${DIM}更多信息请查看: README.md${NC}"
}

# 验证安装
verify_installation() {
    echo ""
    echo -e "${INFO} 验证安装..."
    
    if python3 -c "
import sage
import sage.common
import sage.kernel
import sage.libs
import sage.middleware
print(f'${CHECK} SAGE v{sage.__version__} 安装成功！')
print(f'${CHECK} 所有子包版本一致: {sage.common.__version__}')
" 2>/dev/null; then
        echo -e "${CHECK} 验证通过！"
        return 0
    else
        echo -e "${WARNING} 验证出现问题，但安装可能成功了"
        return 1
    fi
}

# 显示帮助信息
show_help() {
    echo ""
    echo -e "${BOLD}SAGE 快速安装脚本${NC}"
    echo ""
    echo -e "${BLUE}用法：${NC}"
    echo -e "  ./quickstart.sh [安装模式] [环境选项]"
    echo ""
    echo -e "${BLUE}安装模式：${NC}"
    echo ""
    echo -e "  ${BOLD}--minimal, -m${NC}      ${GRAY}最小安装${NC}"
    echo -e "    ${DIM}包含: SAGE核心包 (sage-common, sage-kernel, sage-middleware, sage-libs, sage)${NC}"
    echo -e "    ${DIM}适合: 容器部署、只需要SAGE核心功能的场景${NC}"
    echo ""
    echo -e "  ${BOLD}--standard, -s${NC}     ${GREEN}标准安装 (默认)${NC}"
    echo -e "    ${DIM}包含: SAGE核心包 + 科学计算库 (numpy, pandas, jupyter)${NC}"
    echo -e "    ${DIM}适合: 数据科学、研究、学习${NC}"
    echo ""
    echo -e "  ${BOLD}--dev, -d${NC}          ${YELLOW}开发者安装${NC}"
    echo -e "    ${DIM}包含: 标准安装 + 开发工具 (pytest, black, mypy)${NC}"
    echo -e "    ${DIM}适合: 为SAGE项目贡献代码的开发者${NC}"
    echo ""
    echo -e "${BLUE}环境选项：${NC}"
    echo ""
    echo -e "  ${BOLD}--conda${NC}            ${GREEN}使用 conda 环境 (推荐)${NC}"
    echo -e "    ${DIM}创建独立的conda环境进行安装${NC}"
    echo -e "    ${DIM}提供最佳的环境隔离和依赖管理${NC}"
    echo ""
    echo -e "  ${BOLD}--pip${NC}              仅使用 pip 安装"
    echo -e "    ${DIM}在当前环境中直接使用pip安装${NC}"
    echo ""
    echo -e "  ${BOLD}--help, -h${NC}         显示此帮助"
    echo ""
    echo -e "${BLUE}示例：${NC}"
    echo -e "  ./quickstart.sh                    ${DIM}# 交互式选择${NC}"
    echo -e "  ./quickstart.sh --standard         ${DIM}# 标准安装${NC}"
    echo -e "  ./quickstart.sh --conda --dev      ${DIM}# conda环境中开发者安装${NC}"
    echo -e "  ./quickstart.sh --pip --minimal    ${DIM}# pip最小安装${NC}"
    echo ""
}

# 显示使用提示
show_usage_tips() {
    local mode="$1"
    
    echo ""
    draw_line "─" "$GREEN"
    center_text "${SPARKLES} 快速开始 ${SPARKLES}" "$GREEN$BOLD"
    draw_line "─" "$GREEN"
    echo ""
    
    echo -e "${BLUE}基本使用：${NC}"
    echo -e "  python3 -c \"import sage; print('Hello SAGE!')\""
    echo -e "  sage --help"
    echo ""
    
    case "$mode" in
        "minimal")
            echo -e "${BLUE}最小安装模式：${NC}"
            echo -e "  # 只包含SAGE核心包，适合容器部署"
            echo -e "  python3 -c 'import sage; print(sage.__version__)'"
            echo -e "  # 如需科学计算功能，建议使用 --standard 模式"
            echo ""
            ;;
        "standard")
            echo -e "${BLUE}标准安装模式：${NC}"
            echo -e "  # 包含SAGE核心包和科学计算库"
            echo -e "  jupyter notebook  # 启动Jupyter笔记本"
            echo -e "  jupyter lab       # 启动JupyterLab"
            echo -e "  # 数据科学和研究的完整环境"
            echo ""
            ;;
        "dev")
            echo -e "${BLUE}开发者安装模式：${NC}"
            echo -e "  # 包含完整开发工具链"
            echo -e "  pytest tests/                    # 运行测试"
            echo -e "  black packages/                  # 代码格式化"
            echo -e "  flake8 packages/                 # 代码检查"
            echo -e "  pre-commit run --all-files       # 运行所有检查"
            echo ""
            ;;
    esac
    
    echo -e "${BLUE}文档和示例：${NC}"
    echo -e "  ${GRAY}https://intellistream.github.io/SAGE-Pub/${NC}"
    echo -e "  ${GRAY}./examples/  # 查看示例代码${NC}"
    echo ""
}

# 主函数
main() {
    # 首先检查是否为帮助命令
    for arg in "$@"; do
        if [[ "$arg" == "--help" ]] || [[ "$arg" == "-h" ]] || [[ "$arg" == "help" ]]; then
            show_help
            exit 0
        fi
    done
    
    # 解析命令行参数
    local mode=""
    local use_conda=""
    
    while [[ $# -gt 0 ]]; do
        case "${1}" in
            "--help"|"-h"|"help")
                show_help
                exit 0
                ;;
            "--minimal"|"-m"|"minimal")
                mode="minimal"
                ;;
            "--standard"|"-s"|"standard")
                mode="standard"
                ;;
            "--dev"|"-d"|"dev")
                mode="dev"
                ;;
            "--conda")
                use_conda="true"
                ;;
            "--pip")
                use_conda="false"
                ;;
            *)
                echo -e "${CROSS} 未知选项: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done
    
    # 设置默认模式
    if [ -z "$mode" ]; then
        mode="standard"
    fi
    
    # 设置环境变量
    if [ -n "$use_conda" ]; then
        export SAGE_USE_CONDA="$use_conda"
    fi
    
    # 显示欢迎界面
    show_welcome
    
    # 获取脚本所在目录
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$PROJECT_ROOT"
    
    # 执行安装
    install_sage "$mode"
    
    # 验证安装
    if verify_installation; then
        show_usage_tips "$mode"
        echo ""
        center_text "${ROCKET} 欢迎使用 SAGE！${ROCKET}" "$GREEN$BOLD"
        echo ""
    else
        echo ""
        echo -e "${YELLOW}安装可能成功，请手动验证：${NC}"
        echo -e "  python3 -c \"import sage; print(sage.__version__)\""
    fi
}

# 运行主函数
main "$@"
