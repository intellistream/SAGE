#!/bin/bash
# SAGE 安装脚本 - LOGO 和界面显示
# 包含 SAGE LOGO、欢迎界面等视觉元素

# 导入基础显示工具
source "$(dirname "${BASH_SOURCE[0]}")/basic_display.sh"
source "$(dirname "${BASH_SOURCE[0]}")/output_formatter.sh"

# 显示 SAGE LOGO

# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
AUTO_YES="${AUTO_YES:-false}"
AUTO_CONFIRM="${AUTO_CONFIRM:-false}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

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
        center_text_formatted "https://intellistream.github.io/sage-docs/" "$GRAY"
        center_text_formatted "intellistream 2025" "$GRAY"
    else
        center_text "https://intellistream.github.io/sage-docs/" "$GRAY"
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
    echo -e "  ${BOLD}--standard, -s${NC}     ${GREEN}standard 安装 (默认)${NC}"
    echo -e "    ${DIM}包含: 核心能力 + ML/VDB/streaming 等完整功能依赖${NC}"
    echo -e "    ${DIM}适合: 应用开发、日常使用、大多数用户${NC}"
    echo ""
    echo -e "  ${BOLD}--dev, -d${NC}          ${YELLOW}dev 安装${NC}"
    echo -e "    ${DIM}包含: standard + 开发工具 (sage-dev, pytest, pre-commit)${NC}"
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
    echo -e "  ./quickstart.sh --pip --standard   ${DIM}# pip standard 安装${NC}"
    echo ""
}

# 进度动画工具
_spinner_pid=""
start_spinner() {
    local message="$1"
    if [ -z "$message" ]; then
        message="处理中..."
    fi

    # 使用双层 subshell 彻底隔离 job control 输出
    # 外层 subshell 捕获所有 job 通知，内层运行实际的 spinner
    _spinner_pid=$(
        (
            local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
            local i=0
            while true; do
                printf "\r%s %s" "$message" "${frames[$i]}"
                sleep 0.12
                i=$(((i + 1) % ${#frames[@]}))
            done
        ) &
        echo $!
    )
}

stop_spinner() {
    local final_message="$1"
    if [ -n "$_spinner_pid" ]; then
        kill "$_spinner_pid" 2>/dev/null || true
        wait "$_spinner_pid" 2>/dev/null || true
        _spinner_pid=""
        printf "\r\033[K"
    fi
    if [ -n "$final_message" ]; then
        echo -e "$final_message"
    fi
}

# 显示安装成功信息
show_install_success() {
    local mode="$1"

    echo ""
    echo_icon "🎉" "SAGE 安装成功！" 2 2
    echo ""

    # 显示已安装的内容
    case "$mode" in
        "standard")
            echo -e "${BLUE}已安装 (standard):${NC}"
            echo_icon "✅" "标准功能 + ML/VDB/streaming 等完整依赖" 1 1
            ;;
        "dev")
            echo -e "${BLUE}已安装 (开发模式):${NC}"
            echo_icon "✅" "standard + isage-dev-tools (sage-dev 命令)" 1 1
            echo_icon "✅" "pytest, pre-commit, 代码质量工具" 1 1
            ;;
    esac

    echo ""
    echo -e "${BOLD}快速开始:${NC}"
    echo -e "  ${DIM}# 验证安装（主仓核心表面）${NC}"
    echo -e "  sage verify"
    echo ""
    echo -e "  ${DIM}# 使用 sagellm 直接运行一条真实推理${NC}"
    echo -e "  sage chat --ask \"Hello, SAGE!\""
    echo ""
    echo -e "${DIM}更多信息请查看: README.md${NC}"
}

# 运行 Hello World 示例（动画展示 Pipeline）
run_hello_world_demo() {
    local with_llm="${1:-false}"

    echo ""
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}                       🚀 SAGE 快速体验                                    ${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 验证 SAGE 安装（主仓 in-tree 表面）
    echo -e "${INFO} 验证 SAGE 安装..."
    local sage_version
    sage_version=$(SAGELLM_LOGGING_LEVEL=ERROR python3 -W ignore -c "from sage._version import __version__; import sage.foundation, sage.stream, sage.runtime, sage.serving, sage.cli; print(__version__)" 2>/dev/null | tail -1)
    if [ -n "$sage_version" ]; then
        echo -e "   ${GREEN}✅ SAGE v${sage_version} 已就绪${NC}"
    else
        echo -e "   ${RED}❌ SAGE 未正确安装${NC}"
        return 1
    fi
    echo ""

    if [ "$with_llm" = "true" ]; then
        run_llm_demo
    else
        run_streaming_demo
    fi
}

# 流式处理演示（不需要 LLM）
run_streaming_demo() {
    echo -e "${BLUE}${BOLD}� SAGE 流式数据处理 Pipeline${NC}"
    echo ""
    echo -e "   ${DIM}演示: 实时数据流 → 批处理 → 转换 → 输出${NC}"
    echo ""

    sleep 0.3

    # 展示 Pipeline 结构图
    echo -e "   ┌──────────────────────────────────────────────────────────────────────┐"
    echo -e "   │                                                                      │"
    echo -e "   │    ${CYAN}┌─────────────┐     ┌─────────────┐     ┌─────────────┐${NC}       │"
    echo -e "   │    ${CYAN}│ BatchSource │${NC} ──▶ ${CYAN}│  Transform  │${NC} ──▶ ${CYAN}│    Sink     │${NC}       │"
    echo -e "   │    ${CYAN}│  (生成数据)  │     │  (大写转换) │     │  (输出结果) │${NC}       │"
    echo -e "   │    ${CYAN}└─────────────┘     └─────────────┘     └─────────────┘${NC}       │"
    echo -e "   │                                                                      │"
    echo -e "   └──────────────────────────────────────────────────────────────────────┘"
    echo ""

    sleep 0.5

    echo -e "${BLUE}${BOLD}▶ 执行 Pipeline...${NC}"
    echo ""

    # 动画显示数据流
    local messages=("Hello" "SAGE" "World" "Pipeline" "Demo")
    for i in "${!messages[@]}"; do
        local msg="${messages[$i]}"
        local upper=$(echo "$msg" | tr '[:lower:]' '[:upper:]')
        local num=$((i + 1))
        echo -ne "   ${DIM}[$num]${NC} \"$msg\" "
        sleep 0.15
        echo -ne "──▶ "
        sleep 0.15
        echo -e "${GREEN}\"$upper\"${NC}"
        sleep 0.1
    done

    echo ""
    echo -e "   ${GREEN}✅ 流式处理完成: 5 条数据已处理${NC}"
    echo ""

    # 显示实际代码
    echo -e "${BLUE}${BOLD}📝 示例代码:${NC}"
    echo ""
    echo -e "   ${DIM}from sage.runtime import LocalEnvironment${NC}"
    echo -e "   ${DIM}from sage.foundation import BatchFunction, MapFunction, SinkFunction${NC}"
    echo ""
    echo -e "   ${CYAN}env = LocalEnvironment(\"demo\")${NC}"
    echo -e "   ${CYAN}env.from_batch(Source).map(Transform).sink(Output)${NC}"
    echo -e "   ${CYAN}env.submit(autostop=True)${NC}"
    echo ""

    show_demo_footer
}

# LLM 智能处理演示 - 启动 sage chat (RAG + Pipeline 构建)
run_llm_demo() {
    echo -e "${BLUE}${BOLD}🤖 SAGE 智能编程助手${NC}"
    echo ""
    echo -e "   ${DIM}集成 RAG 检索 + LLM 生成 + Pipeline 构建${NC}"
    echo ""

    sleep 0.3

    # 展示架构图
    echo -e "   ┌──────────────────────────────────────────────────────────────────────┐"
    echo -e "   │                    ${YELLOW}SAGE Chat Pipeline${NC}                                │"
    echo -e "   │                                                                      │"
    echo -e "   │    ${CYAN}┌─────────────┐     ┌─────────────┐     ┌─────────────┐${NC}       │"
    echo -e "   │    ${CYAN}│  User Query │${NC} ──▶ ${CYAN}│  SageVDB RAG │${NC} ──▶ ${CYAN}│  LLM Gen    │${NC}       │"
    echo -e "   │    ${CYAN}│   (问题)    │${NC}     ${CYAN}│  (向量检索) │${NC}     ${CYAN}│   (生成)    │${NC}       │"
    echo -e "   │    ${CYAN}└─────────────┘     └─────────────┘     └─────────────┘${NC}       │"
    echo -e "   │                              │                     │              │"
    echo -e "   │                              ▼                     ▼              │"
    echo -e "   │                      ${GREEN}┌─────────────┐   ┌─────────────┐${NC}        │"
    echo -e "   │                      ${GREEN}│ SAGE Docs   │   │ Qwen2.5     │${NC}        │"
    echo -e "   │                      ${GREEN}│ (知识库)    │   │ (本地 LLM)  │${NC}        │"
    echo -e "   │                      ${GREEN}└─────────────┘   └─────────────┘${NC}        │"
    echo -e "   │                                                                      │"
    echo -e "   │   ${DIM}� 支持: 文档问答 / Pipeline 构建 / 代码生成${NC}                      │"
    echo -e "   └──────────────────────────────────────────────────────────────────────┘"
    echo ""

    sleep 0.5

    # 检查是否有索引（manifest + db 文件）
    local chat_cache_dir
    chat_cache_dir=$(python3 - <<'PY' 2>/dev/null || true
from sage.cli.commands.apps.chat import resolve_index_root
print(resolve_index_root(None))
PY
)
    if [ -z "$chat_cache_dir" ]; then
        local repo_root
        repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
        chat_cache_dir="${repo_root}/.sage/cache/chat"
    fi
    local index_manifest="${chat_cache_dir}/docs_manifest.json"
    local index_db_prefix="${chat_cache_dir}/docs.sagevdb"
    if [ ! -f "$index_manifest" ] || [ ! -f "${index_db_prefix}.config" ]; then
        echo -e "${YELLOW}⚠️  首次运行需要构建文档索引...${NC}"
        echo -e "${DIM}   这将使用本地 Embedding 服务创建向量索引${NC}"
        echo ""

        # 检查 Embedding 服务是否已运行
        local embedding_port=8090
        local embedding_running=false
        # 更可靠的检测：检查返回的 JSON 是否包含 data 数组
        if curl -s --connect-timeout 2 "http://localhost:${embedding_port}/v1/models" 2>/dev/null | grep -q '"data"'; then
            embedding_running=true
        fi

        if [ "$embedding_running" = false ]; then
            echo -e "${YELLOW}ℹ️  未检测到 Embedding 服务，将回退到本地 HF embedding 模型${NC}"
            echo -e "${DIM}   如已自行启动 OpenAI 兼容 embedding endpoint，可稍后使用 --embedding-method openai 与 --embedding-base-url${NC}"
        else
            echo -e "   ${GREEN}✅ 检测到 Embedding 服务 (localhost:${embedding_port})${NC}"
        fi
        echo ""

        echo -ne "${BOLD}是否现在构建索引? [Y/n]: ${NC}"
        read -r build_index
        if [[ ! "$build_index" =~ ^[Nn] ]]; then
            echo ""
            echo -e "${INFO} 正在构建索引..."
            echo ""

            local ingest_log
            ingest_log=$(mktemp)
            local ingest_cmd
            # 设置环境变量抑制各种 INFO 日志
            local quiet_env="SAGELLM_LOGGING_LEVEL=WARNING TRANSFORMERS_VERBOSITY=error HF_HUB_VERBOSITY=error HTTPX_LOG_LEVEL=WARNING"

            if [ "$embedding_running" = true ]; then
                # 使用运行中的 Embedding 服务
                echo -e "${DIM}   使用 Embedding 服务: http://localhost:${embedding_port}/v1${NC}"
                ingest_cmd=(env $quiet_env sage index ingest --quiet --embedding-method openai --embedding-model BAAI/bge-m3 --embedding-base-url "http://localhost:${embedding_port}/v1")
            else
                # 回退到本地 HuggingFace 模型
                echo -e "${DIM}   使用本地 HF 模型: BAAI/bge-m3${NC}"
                ingest_cmd=(env $quiet_env sage index ingest --quiet --embedding-method hf --embedding-model BAAI/bge-m3)
            fi

            start_spinner "   索引构建中，请稍候"
            if "${ingest_cmd[@]}" >"$ingest_log" 2>&1; then
                stop_spinner "   ${GREEN}✅ 索引构建完成${NC}"
            else
                stop_spinner "   ${YELLOW}⚠️  索引构建可能未完成${NC}"
                echo ""
                echo -e "${DIM}   错误信息:${NC}"
                tail -n 10 "$ingest_log"
                echo ""
                echo -e "${DIM}   正在清理不完整的索引文件...${NC}"
                rm -f "${chat_cache_dir}/docs"* 2>/dev/null || true
                echo -e "${YELLOW}⚠️  可以稍后重试:${NC}"
                echo -e "   ${CYAN}sage index ingest --embedding-method hf --embedding-model BAAI/bge-m3${NC}"
                echo -e "   ${CYAN}sage index ingest --embedding-method openai --embedding-model BAAI/bge-m3 --embedding-base-url http://localhost:8090/v1${NC}"
            fi
            rm -f "$ingest_log"
        fi
        echo ""
    fi

    echo -e "${BLUE}${BOLD}▶ 启动 SAGE Chat (RAG 模式)...${NC}"
    echo -e "   ${DIM}输入 'exit'、'quit' 或 Ctrl+C 退出${NC}"
    echo ""

    # 启动 sage chat
    # 优先使用 gateway；若不可用则直接调用 sagellm CLI
    if curl -s http://localhost:8889/v1/models >/dev/null 2>&1; then
        echo -e "   ${GREEN}✅ 检测到本地 LLM gateway (localhost:8889)${NC}"
        # 获取实际运行的模型名称（若可用）
        local local_model
        local_model=$(curl -s http://localhost:8889/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "")
        if [ -n "$local_model" ]; then
            echo -e "   ${DIM}模型: $local_model${NC}"
        fi
        echo ""
        sage chat --engine sagellm --backend auto --model "${local_model:-Qwen/Qwen2.5-0.5B-Instruct}" --stream
    elif command -v sagellm >/dev/null 2>&1; then
        echo -e "   ${GREEN}✅ 未检测到 gateway，改为直接调用 sagellm CLI${NC}"
        echo ""
        sage chat --engine sagellm --backend direct
    elif [ -n "${SAGE_CHAT_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
        echo -e "   ${GREEN}✅ 使用云端 API${NC}"
        echo ""
        sage chat --backend openai --stream
    else
        echo -e "   ${YELLOW}⚠️  未检测到 gateway，也未找到 sagellm 命令${NC}"
        echo -e "   ${DIM}   提示: 运行 'sage serve gateway --json' 查看 gateway 契约，或确认 sagellm 已安装到当前环境${NC}"
    fi

    echo ""

    # 显示示例代码
    echo -e "${BLUE}${BOLD}📝 使用方式:${NC}"
    echo ""
    echo -e "   ${CYAN}# 交互式 RAG 问答${NC}"
    echo -e "   ${DIM}sage chat --engine sagellm --backend auto --stream${NC}"
    echo ""
    echo -e "   ${CYAN}# 单次提问${NC}"
    echo -e "   ${DIM}sage chat --ask \"如何创建 SAGE Pipeline?\" --engine sagellm --backend auto${NC}"
    echo ""
    echo -e "   ${CYAN}# 构建自定义知识库${NC}"
    echo -e "   ${DIM}sage index ingest --source ./my-docs --index my-knowledge${NC}"
    echo ""

    show_demo_footer
}

# 显示演示结尾
show_demo_footer() {
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}                           ✨ 演示完成 ✨                                 ${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "   ${DIM}🎯 探索更多:${NC}"
    echo -e "      ${CYAN}cd examples/tutorials/${NC}    ${DIM}# 教程示例${NC}"
    echo -e "      ${CYAN}cd examples/apps/${NC}         ${DIM}# 应用示例${NC}"
    echo -e "      ${CYAN}sage --help${NC}               ${DIM}# CLI 命令${NC}"
    echo ""
}

# 询问用户是否要继续体验主仓当前可用的能力（chat / hello world）
prompt_start_llm_service() {
    local mode="$1"

    # 在 CI 环境或 --yes 自动模式下跳过
    if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ "${AUTO_YES:-false}" = "true" ] || [ "${AUTO_CONFIRM:-false}" = "true" ]; then
        echo -e "${DIM}提示: 自动跳过服务启动提示 (CI=${CI:-}, AUTO_YES=${AUTO_YES:-false}, AUTO_CONFIRM=${AUTO_CONFIRM:-false})${NC}"
        return 0
    fi

    # standard/dev 模式都支持提示

    # 检查环境是否激活
    local env_activated=true
    if [ -n "${SAGE_ENV_NAME:-}" ] && [ "${CONDA_DEFAULT_ENV:-}" != "${SAGE_ENV_NAME:-}" ]; then
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
        echo -e "  ${CYAN}conda activate ${SAGE_ENV_NAME:-}${NC}"
        echo ""
        echo -e "${DIM}激活后可用以下命令继续体验:${NC}"
        echo -e "  ${CYAN}sage verify${NC}"
        echo -e "  ${CYAN}sage chat --ask \"Hello, SAGE!\"${NC}"
        echo -e "  ${CYAN}sage serve gateway --json${NC}"
        echo ""
        return 0
    fi

    # 显示可用服务选项
    echo -e "${INFO} SAGE 安装完成，您可以："
    echo ""
    echo -e "  ${BOLD}[1] 运行 Hello World${NC}  - 快速体验 SAGE Pipeline"
    echo -e "      ${DIM}运行一个简单的数据处理流水线示例${NC}"
    echo ""
    echo -e "  ${BOLD}[2] 查看 gateway 契约${NC} - 查看外部 sagellm gateway 的启动/探活信息"
    echo -e "      ${DIM}适合需要 OpenAI 兼容接口或联调服务模式时使用${NC}"
    echo ""
    echo -e "  ${BOLD}[3] 跳过${NC}              - 稍后手动操作"
    echo ""

    # 交互式询问
    echo -ne "${BOLD}请选择 [1/2/3]: ${NC}"
    read -r choice

    case "$choice" in
        1)
            echo ""
            echo -e "${INFO} 运行 Hello World Pipeline..."
            echo ""
            run_hello_world_demo false
            ;;
        2)
            echo ""
            echo -e "${INFO} 当前主仓会把 gateway 视为外部 sagellm 集成能力。"
            echo -e "${DIM}可先查看 SAGE 侧约定的启动命令、探活地址与日志路径：${NC}"
            echo ""
            if command -v sage &>/dev/null; then
                sage serve gateway --json || true
                echo ""
                echo -e "${DIM}若已单独启动 gateway，可继续运行：${NC}"
                echo -e "  ${CYAN}sage serve gateway --probe --json${NC}"
                echo -e "  ${CYAN}sage chat --engine sagellm --backend auto --stream${NC}"
            fi
            ;;
        3|"")
            echo ""
            echo -e "${DIM}已跳过。稍后可用以下命令:${NC}"
            echo -e "  ${CYAN}sage verify${NC}"
            echo -e "  ${CYAN}sage chat --ask \"Hello, SAGE!\"${NC}"
            echo -e "  ${CYAN}sage serve gateway --json${NC}"
            ;;
        *)
            echo ""
            echo -e "${DIM}无效选择，已跳过。${NC}"
            ;;
    esac

    echo ""
}

# 显示使用提示
show_usage_tips() {
    local mode="$1"

    echo ""

    # 如果使用了 conda 环境且不在该环境中，显示激活提示
    if [ -n "${SAGE_ENV_NAME:-}" ] && [ "${CONDA_DEFAULT_ENV:-}" != "${SAGE_ENV_NAME:-}" ]; then
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}⚠️  重要：需要激活 Conda 环境${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${INFO} SAGE 已安装到 conda 环境: ${GREEN}${SAGE_ENV_NAME:-}${NC}"
        echo -e "${INFO} 但当前终端未激活该环境"
        echo ""
        echo -e "${BOLD}方式 1: 手动激活（每次打开终端需要运行）${NC}"
        echo -e "  ${CYAN}conda activate ${SAGE_ENV_NAME:-}${NC}"
        echo ""
        echo -e "${BOLD}方式 2: 设置自动激活（推荐）${NC}"
        echo ""
        echo -e "  ${DIM}# 添加到 ~/.bashrc 让终端自动激活${NC}"
        echo -e "  ${CYAN}echo 'conda activate ${SAGE_ENV_NAME:-}' >> ~/.bashrc${NC}"
        echo ""
        echo -e "  ${DIM}# VS Code 用户：在工作区设置中添加以下配置${NC}"
        echo -e "  ${DIM}# 文件: .vscode/settings.json${NC}"
        echo -e "  ${CYAN}{${NC}"
        echo -e "  ${CYAN}  \"python.defaultInterpreterPath\": \"~/miniconda3/envs/${SAGE_ENV_NAME:-}/bin/python\",${NC}"
        echo -e "  ${CYAN}  \"terminal.integrated.env.linux\": {${NC}"
        echo -e "  ${CYAN}    \"CONDA_DEFAULT_ENV\": \"${SAGE_ENV_NAME:-}\"${NC}"
        echo -e "  ${CYAN}  },${NC}"
        echo -e "  ${CYAN}  \"terminal.integrated.shellArgs.linux\": [${NC}"
        echo -e "  ${CYAN}    \"-c\",${NC}"
        echo -e "  ${CYAN}    \"conda activate ${SAGE_ENV_NAME:-} && exec bash\"${NC}"
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
    if [ -n "${SAGE_ENV_NAME:-}" ] && [ "${CONDA_DEFAULT_ENV:-}" != "${SAGE_ENV_NAME:-}" ]; then
        echo -e "  ${DIM}# 首先激活环境:${NC}"
        echo -e "  conda activate ${SAGE_ENV_NAME:-}"
        echo ""
        echo -e "  ${DIM}# 然后使用 SAGE:${NC}"
    fi
    echo -e "  python3 -c \"import sage; print('Hello SAGE!')\""
    echo -e "  sage --help"
    echo ""

    case "$mode" in
        "dev")
            echo -e "${BLUE}开发者模式：${NC}"
            echo -e "  # 包含 standard + 开发工具"
            echo -e "  sage-dev test                    # 运行测试"
            echo -e "  sage-dev quality                 # 代码质量检查"
            echo -e "  pre-commit run --all-files       # 运行所有检查"
            echo ""
            ;;
        "standard"|*)
            echo -e "${BLUE}standard 模式（默认）：${NC}"
            echo -e "  # 包含所有核心功能 + 科学计算 + ML + 向量数据库"
            echo -e "  sage --help                      # 查看 CLI 命令"
            echo -e "  sage-edge --help                 # 查看 edge 聚合 shell（需 serving-edge/full 依赖）"
            echo -e "  jupyter notebook                 # 启动 Jupyter 笔记本"
            echo ""
            ;;
    esac

    # 独立包安装提示（所有模式通用）
    echo -e "${BLUE}独立包（按需安装）：${NC}"
    echo -e "  pip install isage-benchmark             # 性能基准测试"
    echo -e "  pip install isagellm                    # LLM 推理引擎"
    echo -e "  git clone https://github.com/intellistream/sage-examples # 示例代码"
    echo ""

    if [ "$mode" = "dev" ] || [ "$mode" = "standard" ]; then
        echo -e "${BLUE}C++扩展说明（可选）：${NC}"
        echo -e "  ${DIM}# 原生/C++扩展会在安装流程中按需自动构建${NC}"
        echo -e "  ./quickstart.sh --doctor         # 检查本机构建依赖"
        echo -e "  ./quickstart.sh --dev --yes      # 重新执行主仓安装/重建流程"
        echo ""
    fi

    echo -e "${BLUE}文档和示例：${NC}"
    echo -e "  ${GRAY}https://intellistream.github.io/sage-docs/${NC}"
    echo -e "  ${GRAY}./examples/  # 查看示例代码${NC}"
    echo ""

    # 如果是开发模式且使用了 conda 环境，自动配置 VS Code
    if [ "$mode" = "dev" ] && [ -n "${SAGE_ENV_NAME:-}" ]; then
        echo -e "${INFO} 配置 VS Code 开发环境..."

        local vscode_script="$SCRIPT_DIR/../../config/setup_vscode_conda.sh"
        if [ -f "$vscode_script" ]; then
            if bash "$vscode_script" "${SAGE_ENV_NAME:-}" --auto 2>/dev/null; then
                echo -e "${GREEN}✅ VS Code 配置完成${NC}"
                echo -e "${DIM}   终端将自动激活 conda 环境 '${SAGE_ENV_NAME:-}'${NC}"
            else
                echo -e "${YELLOW}⚠️  自动配置失败，可手动运行:${NC}"
                echo -e "  ${CYAN}bash tools/config/setup_vscode_conda.sh ${SAGE_ENV_NAME:-}${NC}"
            fi
        else
            echo -e "${DIM}💡 开发者提示: 运行以下命令配置 VS Code:${NC}"
            echo -e "  ${CYAN}bash tools/config/setup_vscode_conda.sh ${SAGE_ENV_NAME:-}${NC}"
        fi
        echo ""
    fi

    # 安装结束时不自动触发服务启动交互，改为明确可执行的对话指引
    # 默认优先使用 sagellm 非服务模式（run），避免用户额外理解 server/client 拓扑
    echo -e "${BLUE}LLM 对话使用（推荐）：${NC}"
    echo -e "  ${DIM}# 1) 直接使用非服务模式（无需先启动 server）${NC}"
    echo -e "  ${CYAN}sagellm run -p \"Hello, SAGE!\"${NC}"
    echo ""
    echo -e "  ${DIM}# 2) 需要 RAG 交互时，使用 sagellm 引擎直连${NC}"
    echo -e "  ${CYAN}sage chat --engine sagellm --backend auto --stream${NC}"
    echo ""
    echo -e "  ${DIM}# 3) 如需外部 gateway 服务模式，先查看 SAGE 侧契约并探活${NC}"
    echo -e "  ${CYAN}sage serve gateway --json${NC}"
    echo -e "  ${CYAN}sage serve gateway --probe --json${NC}"
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
        "\${workspaceFolder}/src"
  ]
}
EOF

    echo -e "${CHECK} 已创建 VS Code 配置: $settings_file"
    echo -e "${INFO} VS Code 现在会自动激活 conda 环境: $env_name"
    return 0
}
