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

# 显示安装模式选择菜单
show_install_modes() {
    echo ""
    center_text "${GEAR} 请选择安装模式 ${GEAR}" "$BOLD$CYAN"
    echo ""
    
    echo -e "${BLUE}[1]${NC} ${BOLD}快速安装${NC} ${GREEN}(推荐新手)${NC}"
    echo -e "    ${DIM}→ 完整SAGE包 + 所有依赖，30秒搞定${NC}"
    echo -e "    ${DIM}→ 适合：想快速体验SAGE功能${NC}"
    echo ""
    
    echo -e "${BLUE}[2]${NC} ${BOLD}标准安装${NC} ${GREEN}(推荐研究)${NC}"
    echo -e "    ${DIM}→ 完整SAGE包 + 数据科学库 (numpy, pandas, jupyter)${NC}"
    echo -e "    ${DIM}→ 适合：数据分析、科研、学习${NC}"
    echo ""
    
    echo -e "${BLUE}[3]${NC} ${BOLD}SAGE项目开发${NC} ${YELLOW}(贡献代码)${NC}"
    echo -e "    ${DIM}→ 包含测试工具、代码检查、文档生成${NC}"
    echo -e "    ${DIM}→ 适合：想为SAGE项目贡献代码的开发者${NC}"
    echo ""
    
    echo -e "${BLUE}[4]${NC} ${BOLD}应用开发模式${NC} ${CYAN}(使用SAGE)${NC}"
    echo -e "    ${DIM}→ 核心包 + 开发调试配置${NC}"
    echo -e "    ${DIM}→ 适合：用SAGE开发自己应用的开发者${NC}"
    echo ""
    
    echo -e "${BLUE}[5]${NC} ${BOLD}最小安装${NC} ${GRAY}(容器部署)${NC}"
    echo -e "    ${DIM}→ SAGE包但不安装额外的科学计算库${NC}"
    echo -e "    ${DIM}→ 适合：容器环境、不需要数据科学功能${NC}"
    echo ""
    
    echo -e "${BLUE}[6]${NC} ${BOLD}企业版安装${NC} ${PURPLE}(生产环境)${NC}"
    echo -e "    ${DIM}→ 包含企业级功能和高级特性${NC}"
    echo -e "    ${DIM}→ 适合：企业生产部署 (需要许可证)${NC}"
    echo ""
    
    draw_line "─" "$GRAY"
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

check_pip() {
    echo -e "${INFO} 检查 pip..."
    if ! python3 -m pip --version &> /dev/null; then
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
    local mode="${1:-quick}"
    
    echo ""
    echo -e "${GEAR} 开始安装 SAGE 包 (${mode} 模式)..."
    echo ""
    
    # 检查系统环境
    if ! check_python || ! check_pip; then
        echo -e "${CROSS} 环境检查失败，安装终止"
        exit 1
    fi
    
    echo ""
    case "$mode" in
        "quick")
            echo -e "${BLUE}快速安装模式：仅安装核心 SAGE 包${NC}"
            echo -e "${DIM}使用命令: pip install -e .${NC}"
            install_core_packages
            ;;
        "standard")
            echo -e "${BLUE}标准安装模式：核心包 + 科学计算库${NC}"
            echo -e "${DIM}包含: numpy, pandas, matplotlib, scipy, jupyter${NC}"
            install_core_packages
            install_scientific_packages
            ;;
        "development")
            echo -e "${BLUE}SAGE项目开发模式：完整开发工具链${NC}"
            echo -e "${DIM}包含: 测试框架、代码检查、文档工具、pre-commit${NC}"
            install_core_packages
            install_scientific_packages
            install_dev_packages
            setup_sage_dev_environment
            ;;
        "app-dev")
            echo -e "${BLUE}应用开发模式：使用SAGE开发应用${NC}"
            echo -e "${DIM}包含: 核心包 + 调试配置 + 开发工具${NC}"
            install_core_packages
            install_scientific_packages
            setup_app_dev_environment
            ;;
        "minimal")
            echo -e "${BLUE}最小安装模式：仅必需的核心组件${NC}"
            echo -e "${DIM}最小化安装，节省空间${NC}"
            install_minimal_packages
            ;;
        "enterprise")
            echo -e "${BLUE}企业版安装模式：${NC}${PURPLE}包含企业级功能${NC}"
            echo -e "${DIM}正在检查许可证...${NC}"
            if check_enterprise_license; then
                install_core_packages
                install_scientific_packages
                install_enterprise_packages
            else
                echo -e "${CROSS} 企业版许可证验证失败，回退到标准安装"
                install_core_packages
                install_scientific_packages
            fi
            ;;
        *)
            echo -e "${WARNING} 未知安装模式，使用快速安装"
            install_core_packages
            ;;
    esac
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
            if python3 -m pip install -e "$package_path" --quiet; then
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
        if python3 -m pip install "$package" --quiet; then
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
        if python3 -m pip install "$package" --quiet; then
            echo -e "${CHECK} $package 安装成功"
        else
            echo -e "${WARNING} $package 安装可能失败，继续..."
        fi
    done
}

# 最小安装
install_minimal_packages() {
    echo -e "${INFO} 最小化安装核心组件..."
    
    # SAGE 包安装顺序：sage-common → sage-kernel → sage-middleware → sage-libs → sage
    local sage_packages=("sage-common" "sage-kernel" "sage-middleware" "sage-libs" "sage")
    
    for package in "${sage_packages[@]}"; do
        local package_path="packages/$package"
        
        if [ -d "$package_path" ]; then
            echo -e "${DIM}  → 最小安装 $package (开发模式)${NC}"
            if python3 -m pip install -e "$package_path" --quiet; then
                echo -e "${CHECK} $package 安装成功"
            else
                echo -e "${CROSS} $package 安装失败！"
                exit 1
            fi
        else
            echo -e "${WARNING} 跳过不存在的包: $package"
        fi
    done
    
    echo -e "${CHECK} SAGE包安装成功！"
    echo -e "${INFO} 跳过额外的科学计算库安装 (最小化模式)"
    echo -e "${DIM}如需完整功能，建议使用 --standard 模式${NC}"
}

# 检查企业版许可证
check_enterprise_license() {
    if [ -f "tools/license/license_validator.py" ]; then
        echo -e "${INFO} 验证企业版许可证..."
        if python3 tools/license/license_validator.py --quiet 2>/dev/null; then
            echo -e "${CHECK} 企业版许可证验证成功"
            return 0
        else
            echo -e "${WARNING} 企业版许可证验证失败"
            return 1
        fi
    else
        echo -e "${WARNING} 未找到许可证验证工具"
        return 1
    fi
}

# 安装企业版包
install_enterprise_packages() {
    echo -e "${INFO} 安装企业版功能..."
    if [ -f "tools/enterprise/enterprise_manager.py" ]; then
        if python3 tools/enterprise/enterprise_manager.py --install 2>/dev/null; then
            echo -e "${CHECK} 企业版功能安装成功"
        else
            echo -e "${WARNING} 企业版功能安装失败"
        fi
    else
        echo -e "${WARNING} 未找到企业版管理器"
    fi
}

# 设置SAGE项目开发环境（为SAGE项目本身开发）
setup_sage_dev_environment() {
    echo -e "${INFO} 配置SAGE项目开发环境..."
    
    # 设置开发环境变量
    export SAGE_DEBUG=1
    export SAGE_DEV_MODE=1
    export SAGE_LOG_LEVEL=DEBUG
    
    # 创建SAGE项目开发配置文件
    if [ ! -f ".env.sage-dev" ]; then
        cat > .env.sage-dev << EOF
# SAGE 项目开发环境配置 - 用于开发SAGE项目本身
SAGE_DEBUG=1
SAGE_DEV_MODE=1
SAGE_LOG_LEVEL=DEBUG
SAGE_CONFIG_PATH=./config/dev_config.yaml
SAGE_TEST_MODE=1
SAGE_PROFILE_ENABLED=1

# 开发工具配置
PYTHONPATH=\$PWD:\$PWD/packages/sage:\$PWD/packages/sage-common:\$PYTHONPATH
EOF
        echo -e "${CHECK} 创建SAGE开发配置文件 .env.sage-dev"
    fi
    
    # 设置pre-commit hooks
    if command -v pre-commit >/dev/null 2>&1 && [ -f ".pre-commit-config.yaml" ]; then
        echo -e "${INFO} 安装pre-commit hooks..."
        pre-commit install --quiet && echo -e "${CHECK} pre-commit hooks安装成功"
    fi
    
    # 创建开发者文档快捷方式
    echo -e "${INFO} 创建开发者资源..."
    if [ ! -f "DEVELOPMENT.md" ]; then
        cat > DEVELOPMENT.md << EOF
# SAGE 项目开发指南

## 快速开始
\`\`\`bash
source .env.sage-dev
python -m pytest tests/
black packages/
flake8 packages/
\`\`\`

## 开发工作流
1. 创建feature分支
2. 编写代码和测试
3. 运行代码检查: \`black . && flake8 .\`
4. 运行测试: \`pytest\`
5. 提交PR

## 有用的命令
- \`sage --dev-status\` - 查看开发环境状态
- \`python -m sage.tests\` - 运行所有测试
EOF
        echo -e "${CHECK} 创建开发指南 DEVELOPMENT.md"
    fi
    
    echo -e "${CHECK} SAGE项目开发环境配置完成"
    echo -e "${DIM}提示: 运行 'source .env.sage-dev' 激活开发配置${NC}"
}

# 设置应用开发环境（使用SAGE开发自己的应用）
setup_app_dev_environment() {
    echo -e "${INFO} 配置应用开发环境..."
    
    # 设置应用开发环境变量
    export SAGE_APP_DEBUG=1
    export SAGE_VERBOSE=1
    
    # 创建应用开发配置文件
    if [ ! -f ".env.app-dev" ]; then
        cat > .env.app-dev << EOF
# SAGE 应用开发环境配置 - 用于使用SAGE开发自己的应用
SAGE_APP_DEBUG=1
SAGE_VERBOSE=1
SAGE_LOG_LEVEL=INFO
SAGE_CONFIG_PATH=./my_app_config.yaml

# 应用开发相关配置
SAGE_CACHE_ENABLED=1
SAGE_PROFILING=0
SAGE_EXAMPLES_PATH=./examples
EOF
        echo -e "${CHECK} 创建应用开发配置文件 .env.app-dev"
    fi
    
    # 创建示例应用模板
    if [ ! -d "my_sage_app" ]; then
        mkdir -p my_sage_app
        cat > my_sage_app/main.py << EOF
#!/usr/bin/env python3
"""
使用SAGE开发的示例应用
运行: python my_sage_app/main.py
"""

import sage
from sage.common import BaseConfig

def main():
    print(f"🚀 使用 SAGE v{sage.__version__} 开发应用")
    
    # 在这里编写你的应用逻辑
    print("✨ 开始构建你的AI应用...")
    
    # 示例: 基本配置
    # config = BaseConfig()
    
if __name__ == "__main__":
    main()
EOF
        
        cat > my_sage_app/README.md << EOF
# 我的SAGE应用

这是使用SAGE框架开发的示例应用。

## 运行应用
\`\`\`bash
source .env.app-dev
python my_sage_app/main.py
\`\`\`

## 开发提示
- 查看 ./examples/ 目录获取更多示例
- 文档: https://intellistream.github.io/SAGE-Pub/
- 配置文件: my_app_config.yaml
EOF
        echo -e "${CHECK} 创建示例应用模板 my_sage_app/"
    fi
    
    # 创建应用配置模板
    if [ ! -f "my_app_config.yaml" ]; then
        cat > my_app_config.yaml << EOF
# 你的SAGE应用配置文件
app:
  name: "我的SAGE应用"
  version: "1.0.0"
  debug: true

sage:
  log_level: "INFO"
  cache_enabled: true
EOF
        echo -e "${CHECK} 创建应用配置模板 my_app_config.yaml"
    fi
    
    echo -e "${CHECK} 应用开发环境配置完成"
    echo -e "${DIM}提示: 运行 'source .env.app-dev' 激活应用开发配置${NC}"
    echo -e "${DIM}示例: cd my_sage_app && python main.py${NC}"
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

# 获取用户输入的安装模式
get_install_mode() {
    local mode=""
    
    # 检查命令行参数
    case "${1:-}" in
        "--quick"|"-q"|"quick")
            mode="quick"
            ;;
        "--standard"|"-s"|"standard")
            mode="standard"
            ;;
        "--development"|"--dev"|"-d"|"development"|"dev")
            mode="development"
            ;;
        "--app-dev"|"--local"|"app-dev"|"local")
            mode="app-dev"
            ;;
        "--minimal"|"-m"|"minimal")
            mode="minimal"
            ;;
        "--enterprise"|"-e"|"enterprise")
            mode="enterprise"
            ;;
        "--help"|"-h"|"help")
            show_help
            exit 0
            ;;
        "")
            # 交互式选择
            mode="interactive"
            ;;
        *)
            echo -e "${WARNING} 未知参数: $1"
            echo -e "${INFO} 使用 --help 查看帮助"
            mode="quick"
            ;;
    esac
    
    echo "$mode"
}

# 显示帮助信息
show_help() {
    echo ""
    echo -e "${BOLD}SAGE 快速安装脚本${NC}"
    echo ""
    echo -e "${BLUE}用法：${NC}"
    echo -e "  ./quickstart.sh [选项]"
    echo ""
    echo -e "${BLUE}安装模式详解：${NC}"
    echo ""
    echo -e "  ${BOLD}--quick, -q${NC}        ${GREEN}快速安装 (默认)${NC}"
    echo -e "    ${DIM}包含: 完整SAGE包 + 所有依赖${NC}"
    echo -e "    ${DIM}适合: 快速体验SAGE功能${NC}"
    echo -e "    ${DIM}安装时间: ~30秒${NC}"
    echo ""
    echo -e "  ${BOLD}--standard, -s${NC}     ${GREEN}标准安装 (推荐)${NC}"
    echo -e "    ${DIM}包含: 完整SAGE包 + 科学计算库 (numpy, pandas, jupyter)${NC}"
    echo -e "    ${DIM}适合: 数据科学、研究、学习${NC}"
    echo -e "    ${DIM}安装时间: ~2-5分钟${NC}"
    echo ""
    echo -e "  ${BOLD}--development, -d${NC}  ${YELLOW}SAGE项目开发${NC}"
    echo -e "    ${DIM}包含: 标准安装 + 测试工具 + 代码检查 + 文档工具${NC}"
    echo -e "    ${DIM}适合: 为SAGE项目贡献代码的开发者${NC}"
    echo -e "    ${DIM}安装时间: ~5-10分钟${NC}"
    echo ""
    echo -e "  ${BOLD}--app-dev${NC}          ${CYAN}应用开发模式${NC}"
    echo -e "    ${DIM}包含: SAGE核心 + 开发配置 + 调试工具${NC}"
    echo -e "    ${DIM}适合: 使用SAGE开发自己应用的开发者${NC}"
    echo -e "    ${DIM}安装时间: ~1-2分钟${NC}"
    echo ""
    echo -e "  ${BOLD}--minimal, -m${NC}      ${GRAY}最小安装${NC}"
    echo -e "    ${DIM}包含: 完整SAGE包但跳过额外科学计算库${NC}"
    echo -e "    ${DIM}适合: 容器部署、不需要数据科学功能的场景${NC}"
    echo -e "    ${DIM}安装时间: ~30秒${NC}"
    echo ""
    echo -e "  ${BOLD}--enterprise, -e${NC}   ${PURPLE}企业版安装${NC}"
    echo -e "    ${DIM}包含: 标准安装 + 企业级功能 (需要许可证)${NC}"
    echo -e "    ${DIM}适合: 企业生产环境、正式部署${NC}"
    echo -e "    ${DIM}安装时间: ~3-8分钟${NC}"
    echo ""
    echo -e "  ${BOLD}--help, -h${NC}         显示此帮助"
    echo ""
    echo -e "${BLUE}快速选择指南：${NC}"
    echo -e "  ${GREEN}我想快速试试SAGE${NC}           → ${BOLD}--quick${NC}"
    echo -e "  ${GREEN}我要做数据分析/研究${NC}         → ${BOLD}--standard${NC}"
    echo -e "  ${GREEN}我要为SAGE项目写代码${NC}        → ${BOLD}--development${NC}"
    echo -e "  ${GREEN}我要用SAGE开发我的应用${NC}      → ${BOLD}--app-dev${NC}"
    echo -e "  ${GREEN}我要部署到企业生产环境${NC}     → ${BOLD}--enterprise${NC}"
    echo -e "  ${GREEN}我要轻量级/容器部署${NC}        → ${BOLD}--minimal${NC}"
    echo ""
    echo -e "${BLUE}示例：${NC}"
    echo -e "  ./quickstart.sh              ${DIM}# 交互式选择${NC}"
    echo -e "  ./quickstart.sh --standard   ${DIM}# 数据科学环境${NC}"
    echo -e "  ./quickstart.sh --app-dev    ${DIM}# 应用开发环境${NC}"
    echo ""
}

# 确认安装模式
confirm_install_mode() {
    local mode="$1"
    local description=""
    
    case "$mode" in
        "quick") description="快速安装 - 仅核心包" ;;
        "standard") description="标准安装 - 核心包 + 科学计算库" ;;
        "development") description="SAGE项目开发 - 完整工具链 (贡献代码)" ;;
        "app-dev") description="应用开发 - 使用SAGE开发应用" ;;
        "minimal") description="最小安装 - 必需组件" ;;
        "enterprise") description="企业版 - 高级功能" ;;
    esac
    
    echo ""
    draw_line "─" "$GREEN"
    center_text "🎯 安装确认" "$GREEN$BOLD"
    draw_line "─" "$GREEN"
    echo ""
    echo -e "${BLUE}安装模式：${NC} ${BOLD}$description${NC}"
    echo ""
    
    echo -ne "${BLUE}确认开始安装? [Y/n]: ${NC}"
    read -r confirm
    case "$confirm" in
        [nN]|[nN][oO])
            echo -e "${YELLOW}安装已取消${NC}"
            exit 0
            ;;
        *)
            return 0
            ;;
    esac
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
        "development")
            echo -e "${BLUE}SAGE项目开发模式：${NC}"
            echo -e "  # 代码更改会立即生效（editable install）"
            echo -e "  source .env.sage-dev  # 加载SAGE开发配置"
            echo -e "  pre-commit run --all-files  # 运行代码检查"
            echo -e "  pytest tests/  # 运行测试"
            echo ""
            ;;
        "app-dev")
            echo -e "${BLUE}应用开发模式：${NC}"
            echo -e "  source .env.app-dev  # 加载应用开发配置"
            echo -e "  cd my_sage_app && python main.py  # 运行示例应用"
            echo -e "  # 在my_sage_app/目录开发你的应用"
            echo ""
            ;;
        "enterprise")
            echo -e "${BLUE}企业版功能：${NC}"
            echo -e "  # 访问高级企业级功能"
            echo -e "  # 查看许可证状态"
            echo ""
            ;;
        "standard"|"development"|"app-dev")
            echo -e "${BLUE}Jupyter Notebook：${NC}"
            echo -e "  jupyter notebook"
            echo -e "  jupyter lab"
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
    # 检查帮助参数
    if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
        show_help
        exit 0
    fi
    
    # 显示欢迎界面
    show_welcome
    
    # 获取安装模式
    local install_mode=$(get_install_mode "$1")
    
    # 如果是交互式模式，显示选择菜单
    if [[ "$install_mode" == "interactive" ]]; then
        show_install_modes
        while true; do
            echo -ne "${BLUE}请选择安装模式 [1-6]: ${NC}"
            read -r choice
            case $choice in
                1) install_mode="quick"; break ;;
                2) install_mode="standard"; break ;;
                3) install_mode="development"; break ;;
                4) install_mode="app-dev"; break ;;
                5) install_mode="minimal"; break ;;
                6) install_mode="enterprise"; break ;;
                *) echo -e "${WARNING} 无效选择，请输入 1-6" ;;
            esac
        done
    fi
    
    # 确认安装模式 (除非是命令行直接指定)
    if [[ $# -eq 0 ]]; then
        confirm_install_mode "$install_mode"
    fi
    
    # 获取脚本所在目录
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$PROJECT_ROOT"
    
    # 执行安装
    install_sage "$install_mode"
    
    # 验证安装
    if verify_installation; then
        show_usage_tips "$install_mode"
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
