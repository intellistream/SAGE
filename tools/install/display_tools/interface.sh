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

    # LOGO 始终居中显示，不需要额外偏移

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

# 询问用户是否要启动服务（LLM / Studio）
prompt_start_llm_service() {
    local mode="$1"

    # 在 CI 环境或 --yes 自动模式下跳过
    if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] || [ "$AUTO_YES" = "true" ]; then
        return 0
    fi

    # 只在 dev/full 模式下询问（core/standard 模式可能没有完整的服务支持）
    if [ "$mode" = "core" ]; then
        return 0
    fi

    # 检查是否有 GPU 可用
    local has_gpu=false
    if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
        has_gpu=true
    fi

    # 检查环境是否激活
    local env_activated=true
    if [ -n "$SAGE_ENV_NAME" ] && [ "$CONDA_DEFAULT_ENV" != "$SAGE_ENV_NAME" ]; then
        env_activated=false
    fi

    echo ""
    draw_line "─" "$CYAN"
    echo -e "${CYAN}${BOLD}🚀 快速启动服务${NC}"
    draw_line "─" "$CYAN"
    echo ""

    # 如果环境未激活，显示提示后返回
    if [ "$env_activated" = false ]; then
        echo -e "${YELLOW}⚠️  请先激活 conda 环境后再启动服务:${NC}"
        echo -e "  ${CYAN}conda activate $SAGE_ENV_NAME${NC}"
        echo ""
        echo -e "${DIM}激活后可用以下命令启动服务:${NC}"
        echo -e "  ${CYAN}sage llm serve${NC}       # 启动 LLM 推理服务"
        echo -e "  ${CYAN}sage studio start${NC}   # 启动 Studio Web 界面"
        echo ""
        return 0
    fi

    # 显示可用服务选项
    echo -e "${INFO} SAGE 提供以下服务，您可以选择启动："
    echo ""
    echo -e "  ${BOLD}[1] sage llm serve${NC}    - LLM 推理服务 (OpenAI 兼容 API)"
    if [ "$has_gpu" = true ]; then
        echo -e "      ${DIM}提供 http://localhost:8901/v1，支持本地大模型推理${NC}"
    else
        echo -e "      ${DIM}${YELLOW}⚠️  需要 GPU，当前未检测到${NC}"
    fi
    echo ""
    echo -e "  ${BOLD}[2] sage studio start${NC} - Studio Web 界面 (包含 LLM)"
    if [ "$mode" = "full" ] || [ "$mode" = "dev" ]; then
        echo -e "      ${DIM}图形化界面，http://localhost:5173，包含 Chat/RAG/微调等功能${NC}"
    else
        echo -e "      ${DIM}${YELLOW}⚠️  需要 --full 或 --dev 模式安装${NC}"
    fi
    echo ""
    echo -e "  ${BOLD}[3] 跳过${NC}              - 稍后手动启动"
    echo ""

    # 交互式询问
    echo -ne "${BOLD}请选择要启动的服务 [1/2/3]: ${NC}"
    read -r choice

    case "$choice" in
        1)
            if [ "$has_gpu" = true ]; then
                echo ""
                echo -e "${INFO} 正在启动 LLM 服务..."
                echo -e "${DIM}   首次启动会下载模型（Qwen2.5-0.5B，约 300MB）...${NC}"
                echo ""

                if command -v sage &>/dev/null; then
                    sage llm serve 2>&1 | head -25
                    echo ""
                    echo -e "${GREEN}✅ LLM 服务已启动${NC}"
                    echo -e "${DIM}   API 地址: http://localhost:8901/v1${NC}"
                    echo -e "${DIM}   状态查看: sage llm status${NC}"
                    echo -e "${DIM}   停止服务: sage llm stop${NC}"
                else
                    echo -e "${YELLOW}⚠️  sage 命令不可用，请手动启动:${NC}"
                    echo -e "  ${CYAN}sage llm serve${NC}"
                fi
            else
                echo ""
                echo -e "${YELLOW}⚠️  未检测到 GPU，无法启动本地 LLM 服务。${NC}"
                echo -e "${DIM}您可以配置云端 API 作为替代（在 .env 文件中设置）:${NC}"
                echo -e "  ${CYAN}SAGE_CHAT_API_KEY=sk-xxx${NC}"
                echo -e "  ${CYAN}SAGE_CHAT_BASE_URL=https://api.openai.com/v1${NC}"
            fi
            ;;
        2)
            if [ "$mode" = "full" ] || [ "$mode" = "dev" ]; then
                echo ""
                echo -e "${INFO} 正在启动 SAGE Studio..."
                echo -e "${DIM}   这将同时启动前端界面和后端服务${NC}"
                if [ "$has_gpu" = true ]; then
                    echo -e "${DIM}   首次启动会下载 LLM 模型...${NC}"
                fi
                echo ""

                if command -v sage &>/dev/null; then
                    # Studio 启动可能需要更长时间，显示更多输出
                    sage studio start 2>&1 | head -30
                    echo ""
                    echo -e "${GREEN}✅ Studio 已启动${NC}"
                    echo -e "${DIM}   访问地址: http://localhost:5173${NC}"
                    echo -e "${DIM}   状态查看: sage studio status${NC}"
                    echo -e "${DIM}   停止服务: sage studio stop${NC}"
                else
                    echo -e "${YELLOW}⚠️  sage 命令不可用，请手动启动:${NC}"
                    echo -e "  ${CYAN}sage studio start${NC}"
                fi
            else
                echo ""
                echo -e "${YELLOW}⚠️  Studio 需要 --full 或 --dev 模式安装。${NC}"
                echo -e "${DIM}请使用以下命令重新安装:${NC}"
                echo -e "  ${CYAN}./quickstart.sh --full${NC}"
                echo -e "  ${CYAN}./quickstart.sh --dev${NC}"
            fi
            ;;
        3|"")
            echo ""
            echo -e "${DIM}已跳过。稍后可用以下命令启动服务:${NC}"
            echo -e "  ${CYAN}sage llm serve${NC}       # LLM 推理服务"
            echo -e "  ${CYAN}sage studio start${NC}   # Studio Web 界面"
            ;;
        *)
            echo ""
            echo -e "${DIM}无效选择，已跳过。稍后可用以下命令启动:${NC}"
            echo -e "  ${CYAN}sage llm serve${NC}"
            echo -e "  ${CYAN}sage studio start${NC}"
            ;;
    esac

    echo ""
}

# 显示使用提示
show_usage_tips() {
    local mode="$1"

    echo ""

    # 如果使用了 conda 环境且不在该环境中，显示激活提示
    if [ -n "$SAGE_ENV_NAME" ] && [ "$CONDA_DEFAULT_ENV" != "$SAGE_ENV_NAME" ]; then
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}⚠️  重要：需要激活 Conda 环境${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${INFO} SAGE 已安装到 conda 环境: ${GREEN}$SAGE_ENV_NAME${NC}"
        echo -e "${INFO} 但当前终端未激活该环境"
        echo ""
        echo -e "${BOLD}方式 1: 手动激活（每次打开终端需要运行）${NC}"
        echo -e "  ${CYAN}conda activate $SAGE_ENV_NAME${NC}"
        echo ""
        echo -e "${BOLD}方式 2: 设置自动激活（推荐）${NC}"
        echo ""
        echo -e "  ${DIM}# 添加到 ~/.bashrc 让终端自动激活${NC}"
        echo -e "  ${CYAN}echo 'conda activate $SAGE_ENV_NAME' >> ~/.bashrc${NC}"
        echo ""
        echo -e "  ${DIM}# VS Code 用户：在工作区设置中添加以下配置${NC}"
        echo -e "  ${DIM}# 文件: .vscode/settings.json${NC}"
        echo -e "  ${CYAN}{${NC}"
        echo -e "  ${CYAN}  \"python.defaultInterpreterPath\": \"~/miniconda3/envs/$SAGE_ENV_NAME/bin/python\",${NC}"
        echo -e "  ${CYAN}  \"terminal.integrated.env.linux\": {${NC}"
        echo -e "  ${CYAN}    \"CONDA_DEFAULT_ENV\": \"$SAGE_ENV_NAME\"${NC}"
        echo -e "  ${CYAN}  },${NC}"
        echo -e "  ${CYAN}  \"terminal.integrated.shellArgs.linux\": [${NC}"
        echo -e "  ${CYAN}    \"-c\",${NC}"
        echo -e "  ${CYAN}    \"conda activate $SAGE_ENV_NAME && exec bash\"${NC}"
        echo -e "  ${CYAN}  ]${NC}"
        echo -e "  ${CYAN}}${NC}"
        echo ""
        echo -e "${DIM}激活环境后，您才能使用 SAGE 的所有命令和功能${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
    fi

    draw_line "─" "$GREEN"
    echo_icon "✨" "快速开始" 2 2
    draw_line "─" "$GREEN"
    echo ""

    echo -e "${BLUE}基本使用：${NC}"
    if [ -n "$SAGE_ENV_NAME" ] && [ "$CONDA_DEFAULT_ENV" != "$SAGE_ENV_NAME" ]; then
        echo -e "  ${DIM}# 首先激活环境:${NC}"
        echo -e "  conda activate $SAGE_ENV_NAME"
        echo ""
        echo -e "  ${DIM}# 然后使用 SAGE:${NC}"
    fi
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

    # 如果是开发模式且使用了 conda 环境，自动配置 VS Code
    if [ "$mode" = "dev" ] && [ -n "$SAGE_ENV_NAME" ]; then
        echo -e "${INFO} 配置 VS Code 开发环境..."

        local vscode_script="$SCRIPT_DIR/../../config/setup_vscode_conda.sh"
        if [ -f "$vscode_script" ]; then
            if bash "$vscode_script" "$SAGE_ENV_NAME" --auto 2>/dev/null; then
                echo -e "${GREEN}✅ VS Code 配置完成${NC}"
                echo -e "${DIM}   终端将自动激活 conda 环境 '$SAGE_ENV_NAME'${NC}"
            else
                echo -e "${YELLOW}⚠️  自动配置失败，可手动运行:${NC}"
                echo -e "  ${CYAN}bash tools/config/setup_vscode_conda.sh $SAGE_ENV_NAME${NC}"
            fi
        else
            echo -e "${DIM}💡 开发者提示: 运行以下命令配置 VS Code:${NC}"
            echo -e "  ${CYAN}bash tools/config/setup_vscode_conda.sh $SAGE_ENV_NAME${NC}"
        fi
        echo ""
    fi

    # 询问用户是否要启动 LLM 服务（非 CI 环境 + 非 --yes 自动模式）
    prompt_start_llm_service "$mode"
}

# 创建 VS Code conda 环境配置的辅助函数
create_vscode_conda_config() {
    local env_name="$1"
    local workspace_root="${2:-.}"
    local conda_path="${3:-~/miniconda3}"

    # 创建 .vscode 目录
    mkdir -p "$workspace_root/.vscode"

    local settings_file="$workspace_root/.vscode/settings.json"

    # 检查是否已存在配置文件
    if [ -f "$settings_file" ]; then
        echo -e "${WARNING} VS Code 配置文件已存在: $settings_file"
        echo -e "${INFO} 请手动添加以下配置:"
        echo ""
        echo -e "  \"python.defaultInterpreterPath\": \"$conda_path/envs/$env_name/bin/python\","
        echo -e "  \"terminal.integrated.shellArgs.linux\": [\"-c\", \"conda activate $env_name && exec bash\"]"
        echo ""
        return 1
    fi

    # 创建新配置文件
    cat > "$settings_file" << EOF
{
  "python.defaultInterpreterPath": "$conda_path/envs/$env_name/bin/python",
  "terminal.integrated.env.linux": {
    "CONDA_DEFAULT_ENV": "$env_name"
  },
  "terminal.integrated.shellArgs.linux": [
    "-c",
    "conda activate $env_name && exec bash"
  ],
  "python.terminal.activateEnvironment": true,
  "python.analysis.extraPaths": [
    "\${workspaceFolder}/packages/sage/src",
    "\${workspaceFolder}/packages/sage-common/src",
    "\${workspaceFolder}/packages/sage-kernel/src",
    "\${workspaceFolder}/packages/sage-libs/src",
    "\${workspaceFolder}/packages/sage-middleware/src",
    "\${workspaceFolder}/packages/sage-platform/src",
    "\${workspaceFolder}/packages/sage-apps/src",
    "\${workspaceFolder}/packages/sage-studio/src",
    "\${workspaceFolder}/packages/sage-tools/src",
    "\${workspaceFolder}/packages/sage-cli/src",
    "\${workspaceFolder}/packages/sage-gateway/src"
  ]
}
EOF

    echo -e "${CHECK} 已创建 VS Code 配置: $settings_file"
    echo -e "${INFO} VS Code 现在会自动激活 conda 环境: $env_name"
    return 0
}
