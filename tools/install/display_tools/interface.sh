#!/bin/bash
# SAGE 安装脚本 - LOGO 和界面显示
# 包含 SAGE LOGO、欢迎界面等视觉元素

# 导入基础显示工具
source "$(dirname "${BASH_SOURCE[0]}")/basic_display.sh"
source "$(dirname "${BASH_SOURCE[0]}")/output_formatter.sh"

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

    # 如果启用了偏移，为 LOGO 添加额外偏移
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        # LOGO 偏移量，用户可通过环境变量自定义

        local logo_offset="${SAGE_LOGO_OFFSET:-30}"  # 默认6个字符的额外偏移
        padding=$((padding + logo_offset))
    fi

    local spaces=""
    for (( i=0; i<padding; i++ )); do
        spaces+=" "
    done

    for line in "${logo_lines[@]}"; do
        printf "%s%b%s%b\n" "$spaces" "$CYAN$BOLD" "$line" "$NC"
    done

    echo ""

    # 网址和版权信息也应用相同的偏移逻辑
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        center_text_formatted "https://intellistream.github.io/SAGE-Pub/" "$GRAY"
        center_text_formatted "intellistream 2025" "$GRAY"
    else
        center_text "https://intellistream.github.io/SAGE-Pub/" "$GRAY"
        center_text "intellistream 2025" "$GRAY"
    fi
}

# 显示欢迎界面
show_welcome() {
    clear
    echo ""

    # 使用与 LOGO 对齐的显示方式，确保 🚀 图标与下面的 S 字母对齐
    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        draw_line_formatted
        # 在偏移环境中也使用 LOGO 对齐
        align_with_logo "🚀 欢迎使用 SAGE 快速部署脚本" "$BOLD$WHITE"
        draw_line_formatted
    else
        draw_line
        # 使用 LOGO 对齐而不是居中对齐
        align_with_logo "🚀 欢迎使用 SAGE 快速部署脚本" "$BOLD$WHITE"
        draw_line
    fi

    show_logo

    if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
        draw_line_formatted
    else
        draw_line
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
    echo -e "  ${BOLD}--core, -c${NC}         ${GRAY}核心框架 (L1-L4)${NC}"
    echo -e "    ${DIM}包含: common, platform, kernel, libs, middleware${NC}"
    echo -e "    ${DIM}适合: 容器部署、生产运行、最小依赖${NC}"
    echo ""
    echo -e "  ${BOLD}--standard, -s${NC}     ${GREEN}标准版本 (推荐)${NC}"
    echo -e "    ${DIM}包含: Core + sage CLI + 科学计算包 (numpy, pandas, matplotlib)${NC}"
    echo -e "    ${DIM}适合: 应用开发、日常使用、大多数用户${NC}"
    echo ""
    echo -e "  ${BOLD}--full, -f${NC}         ${PURPLE}完整功能${NC}"
    echo -e "    ${DIM}包含: Standard + apps, benchmark, studio (Web UI)${NC}"
    echo -e "    ${DIM}适合: 需要示例应用和可视化界面${NC}"
    echo ""
    echo -e "  ${BOLD}--dev, -d${NC}          ${YELLOW}开发模式 (默认)${NC}"
    echo -e "    ${DIM}包含: Full + sage-tools (sage-dev, pytest, pre-commit)${NC}"
    echo -e "    ${DIM}适合: 贡献 SAGE 框架源码、运行测试${NC}"
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
    echo -e "  ./quickstart.sh --pip --core       ${DIM}# pip核心运行时安装${NC}"
    echo ""
}

# 显示安装成功信息
show_install_success() {
    local mode="$1"

    echo ""
    echo_icon "🎉" "SAGE 安装成功！" 2 2
    echo ""

    # 显示已安装的内容
    case "$mode" in
        "core")
            echo -e "${BLUE}已安装 (核心框架):${NC}"
            echo_icon "✅" "L1-L4: common, platform, kernel, libs, middleware" 1 1
            ;;
        "standard")
            echo -e "${BLUE}已安装 (标准版本):${NC}"
            echo_icon "✅" "Core + sage CLI + 科学计算包" 1 1
            echo_icon "✅" "numpy, pandas, matplotlib, scipy, jupyter" 1 1
            ;;
        "full")
            echo -e "${BLUE}已安装 (完整功能):${NC}"
            echo_icon "✅" "Standard + apps, benchmark, studio" 1 1
            echo_icon "✅" "示例应用 + Web UI 可视化界面" 1 1
            ;;
        "dev")
            echo -e "${BLUE}已安装 (开发模式):${NC}"
            echo_icon "✅" "Full + sage-tools (sage-dev 命令)" 1 1
            echo_icon "✅" "pytest, pre-commit, 代码质量工具" 1 1
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

# 显示使用提示
show_usage_tips() {
    local mode="$1"

    echo ""
    draw_line "─" "$GREEN"
    echo_icon "✨" "快速开始" 2 2
    draw_line "─" "$GREEN"
    echo ""

    echo -e "${BLUE}基本使用：${NC}"
    echo -e "  python3 -c \"import sage; print('Hello SAGE!')\""
    echo -e "  sage --help"
    echo ""

    case "$mode" in
        "core")
            echo -e "${BLUE}核心运行时模式：${NC}"
            echo -e "  # 只包含 SAGE 核心包 (L1-L4)，适合容器部署和生产环境"
            echo -e "  python3 -c 'from sage.kernel import Pipeline; print(\"Pipeline ready\")'"
            echo -e "  # 如需完整功能，建议使用 --standard 或 --dev 模式"
            echo ""
            ;;
        "standard")
            echo -e "${BLUE}标准模式：${NC}"
            echo -e "  # 包含 Core + CLI + 科学计算包"
            echo -e "  sage --help                      # 查看 CLI 命令"
            echo -e "  jupyter notebook                 # 启动 Jupyter 笔记本"
            echo -e "  python examples/tutorials/hello_world.py  # 运行示例"
            echo ""
            ;;
        "full")
            echo -e "${BLUE}完整功能模式：${NC}"
            echo -e "  # 包含 Standard + Apps + Studio (Web UI)"
            echo -e "  sage web-ui start                # 启动 Web UI"
            echo -e "  python examples/apps/rag_app.py  # 运行应用示例"
            echo ""
            ;;
        "dev")
            echo -e "${BLUE}开发者模式：${NC}"
            echo -e "  # 包含完整开发工具链"
            echo -e "  sage-dev test                    # 运行测试"
            echo -e "  sage-dev quality                 # 代码质量检查"
            echo -e "  sage-dev examples test           # 测试所有示例"
            echo -e "  pre-commit run --all-files       # 运行所有检查"
            echo ""
            echo -e "${BLUE}C++扩展管理（可选）：${NC}"
            echo -e "  ${DIM}# C++扩展已在安装 sage-middleware 时自动构建${NC}"
            echo -e "  sage extensions status           # 检查扩展状态"
            echo -e "  sage extensions install --force  # 强制重新构建扩展"
            echo ""
            ;;
    esac

    echo -e "${BLUE}文档和示例：${NC}"
    echo -e "  ${GRAY}https://intellistream.github.io/SAGE-Pub/${NC}"
    echo -e "  ${GRAY}./examples/  # 查看示例代码${NC}"
    echo ""
}
