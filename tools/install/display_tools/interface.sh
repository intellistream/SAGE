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
    echo -e "  ${DIM}# 验证安装（PEP 420 namespace）${NC}"
    echo -e "  python3 -c 'import sage.common; print(f\"SAGE v{sage.common.__version__} 安装成功！\")'"
    echo ""
    echo -e "  ${DIM}# 运行示例${NC}"
    echo -e "  cd examples && python3 rag/basic_rag.py"
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

    # 验证 SAGE 安装（PEP 420 namespace - 检查实际包）
    echo -e "${INFO} 验证 SAGE 安装..."
    local sage_version
    sage_version=$(VLLM_LOGGING_LEVEL=ERROR python3 -W ignore -c "import sage.common; print(sage.common.__version__)" 2>/dev/null | tail -1)
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
    echo -e "   ${DIM}from sage.kernel.api import LocalEnvironment${NC}"
    echo -e "   ${DIM}from sage.common.core.functions import BatchFunction, MapFunction, SinkFunction${NC}"
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
    local index_manifest="${chat_cache_dir}/docs-public_manifest.json"
    local index_db_prefix="${chat_cache_dir}/docs-public.sagevdb"
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
            echo -e "${YELLOW}ℹ️  Embedding 服务未运行，需要先启动${NC}"
            echo -ne "${BOLD}是否启动 LLM + Embedding 服务? [Y/n]: ${NC}"
            read -r start_services
            if [[ ! "$start_services" =~ ^[Nn] ]]; then
                echo ""
                echo -e "${INFO} 启动 LLM + Embedding 服务..."
                echo -e "${DIM}   首次启动需要下载模型并加载到 GPU，可能需要 2-4 分钟${NC}"
                echo -e "${DIM}   • LLM 模型: Qwen2.5-0.5B (~300MB)${NC}"
                echo -e "${DIM}   • Embedding 模型: bge-small-zh (~100MB)${NC}"
                echo ""
                # 后台启动服务
                # 注意: sage llm serve 默认已包含 embedding 服务
                sage llm serve &>/dev/null &
                local serve_pid=$!

                # 等待 Embedding 服务就绪，同时显示进度
                local wait_count=0
                local max_wait=90  # 最多等待 180 秒 (90 * 2)
                echo -e "   ${CYAN}⏳ 等待服务启动（LLM 加载到 GPU 需要时间）...${NC}"
                while [ $wait_count -lt $max_wait ]; do
                    if curl -s --connect-timeout 2 "http://localhost:${embedding_port}/v1/models" 2>/dev/null | grep -q '"data"'; then
                        embedding_running=true
                        break
                    fi
                    # 显示经过时间
                    local elapsed=$((wait_count * 2))
                    printf "\r   ${DIM}已等待 %ds...${NC}" $elapsed
                    sleep 2
                    wait_count=$((wait_count + 1))
                done
                printf "\r\033[K"  # 清除进度行

                if [ "$embedding_running" = true ]; then
                    echo -e "   ${GREEN}✅ Embedding 服务已就绪${NC}"
                else
                    echo -e "   ${YELLOW}⚠️  Embedding 服务启动超时，使用本地 HF 模型${NC}"
                    echo -e "   ${DIM}提示: 服务可能仍在后台启动中，可稍后检查 sage llm status${NC}"
                fi
            fi
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
            local quiet_env="VLLM_LOGGING_LEVEL=WARNING TRANSFORMERS_VERBOSITY=error HF_HUB_VERBOSITY=error HTTPX_LOG_LEVEL=WARNING"

            if [ "$embedding_running" = true ]; then
                # 使用运行中的 Embedding 服务
                echo -e "${DIM}   使用 Embedding 服务: http://localhost:${embedding_port}/v1${NC}"
                ingest_cmd=(env $quiet_env sage chat ingest --quiet --embedding-method openai --embedding-model BAAI/bge-m3 --embedding-base-url "http://localhost:${embedding_port}/v1")
            else
                # 回退到本地 HuggingFace 模型
                echo -e "${DIM}   使用本地 HF 模型: BAAI/bge-m3${NC}"
                ingest_cmd=(env $quiet_env sage chat ingest --quiet --embedding-method hf --embedding-model BAAI/bge-m3)
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
                rm -f "${chat_cache_dir}/docs-public"* 2>/dev/null || true
                echo -e "${YELLOW}⚠️  可以稍后重试:${NC}"
                echo -e "   ${CYAN}sage llm serve${NC}  # 启动 LLM + Embedding 服务"
                echo -e "   ${CYAN}sage chat ingest --embedding-method openai --embedding-model BAAI/bge-m3 --embedding-base-url http://localhost:8090/v1${NC}"
            fi
            rm -f "$ingest_log"
        fi
        echo ""
    fi

    echo -e "${BLUE}${BOLD}▶ 启动 SAGE Chat (RAG 模式)...${NC}"
    echo -e "   ${DIM}输入 'exit'、'quit' 或 Ctrl+C 退出${NC}"
    echo ""

    # 启动 sage chat
    # 优先使用本地 vLLM，如果没有则用 mock
    if curl -s http://localhost:8901/v1/models >/dev/null 2>&1; then
        echo -e "   ${GREEN}✅ 检测到本地 LLM 服务 (localhost:8901)${NC}"
        # 获取实际运行的模型名称
        local vllm_model
        vllm_model=$(curl -s http://localhost:8901/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "")
        if [ -n "$vllm_model" ]; then
            echo -e "   ${DIM}模型: $vllm_model${NC}"
        fi
        echo ""
        sage chat --backend vllm --base-url http://localhost:8901/v1 --model "${vllm_model:-Qwen/Qwen2.5-0.5B-Instruct}" --stream
    elif [ -n "${SAGE_CHAT_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
        echo -e "   ${GREEN}✅ 使用云端 API${NC}"
        echo ""
        sage chat --backend openai --stream
    else
        echo -e "   ${YELLOW}ℹ️  使用 Mock 模式演示 (无需 LLM 服务)${NC}"
        echo -e "   ${DIM}   提示: 运行 'sage llm serve' 可启动本地 LLM${NC}"
        echo ""
        sage chat --backend mock
    fi

    echo ""

    # 显示示例代码
    echo -e "${BLUE}${BOLD}📝 使用方式:${NC}"
    echo ""
    echo -e "   ${CYAN}# 交互式 RAG 问答${NC}"
    echo -e "   ${DIM}sage chat --backend vllm --base-url http://localhost:8901/v1${NC}"
    echo ""
    echo -e "   ${CYAN}# 单次提问${NC}"
    echo -e "   ${DIM}sage chat --ask \"如何创建 SAGE Pipeline?\" --backend vllm${NC}"
    echo ""
    echo -e "   ${CYAN}# 构建自定义知识库${NC}"
    echo -e "   ${DIM}sage chat ingest --source ./my-docs --index my-knowledge${NC}"
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

# 询问用户是否要启动服务（LLM / Studio / Hello World）
prompt_start_llm_service() {
    local mode="$1"

    # 在 CI 环境或 --yes 自动模式下跳过
    if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ "${AUTO_YES:-false}" = "true" ] || [ "${AUTO_CONFIRM:-false}" = "true" ]; then
        echo -e "${DIM}提示: 自动跳过服务启动提示 (CI=${CI:-}, AUTO_YES=${AUTO_YES:-false}, AUTO_CONFIRM=${AUTO_CONFIRM:-false})${NC}"
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
        echo -e "${DIM}激活后可用以下命令启动服务:${NC}"
        echo -e "  ${CYAN}sage llm serve${NC}       # 启动 LLM 推理服务"
        echo -e "  ${CYAN}sage studio start${NC}   # 启动 Studio Web 界面"
        echo ""
        return 0
    fi

    # 显示可用服务选项
    echo -e "${INFO} SAGE 安装完成，您可以："
    echo ""
    echo -e "  ${BOLD}[1] 运行 Hello World${NC}  - 快速体验 SAGE Pipeline"
    echo -e "      ${DIM}运行一个简单的数据处理流水线示例${NC}"
    echo ""
    echo -e "  ${BOLD}[2] sage llm serve${NC}    - 启动 LLM 推理服务"
    if [ "$has_gpu" = true ]; then
        echo -e "      ${DIM}提供 OpenAI 兼容 API (http://localhost:8901/v1)${NC}"
    else
        echo -e "      ${DIM}${YELLOW}⚠️  需要 GPU，当前未检测到${NC}"
    fi
    echo ""
    echo -e "  ${BOLD}[3] sage studio start${NC} - 启动 Studio Web 界面"
    if [ "$mode" = "full" ] || [ "$mode" = "dev" ]; then
        echo -e "      ${DIM}图形化界面 (http://localhost:5173)，含 Chat/RAG 等功能${NC}"
    else
        echo -e "      ${DIM}${YELLOW}⚠️  需要 --full 或 --dev 模式安装${NC}"
    fi
    echo ""
    echo -e "  ${BOLD}[4] 跳过${NC}              - 稍后手动操作"
    echo ""

    # 交互式询问
    echo -ne "${BOLD}请选择 [1/2/3/4]: ${NC}"
    read -r choice

    case "$choice" in
        1)
            echo ""
            echo -e "${INFO} 运行 Hello World Pipeline..."
            echo ""
            run_hello_world_demo false
            ;;
        2)
            if [ "$has_gpu" = true ]; then
                echo ""
                echo -e "${INFO} 正在启动 LLM 服务..."
                echo -e "${DIM}   首次启动会下载模型并加载到 GPU，可能需要 1-3 分钟${NC}"
                echo -e "${DIM}   • 模型下载: Qwen2.5-0.5B (~300MB)${NC}"
                echo -e "${DIM}   • GPU 加载: vLLM 初始化${NC}"
                echo ""

                if command -v sage &>/dev/null; then
                    # 后台启动并实时显示进度
                    local llm_log="/tmp/sage_llm_serve_$$.log"

                    # 启动服务（后台运行）
                    sage llm serve > "$llm_log" 2>&1 &
                    local sage_pid=$!

                    # 显示实时进度，同时监控日志
                    local elapsed=0
                    local max_wait=180  # 最多等待 3 分钟
                    local last_status=""

                    while kill -0 $sage_pid 2>/dev/null && [ $elapsed -lt $max_wait ]; do
                        # 尝试从日志中获取当前状态
                        if [ -f "$llm_log" ]; then
                            # 检测关键状态
                            if grep -q "下载位置" "$llm_log" 2>/dev/null && [ "$last_status" != "downloading" ]; then
                                printf "\r\033[K"
                                echo -e "   ${CYAN}⏳ 正在下载模型...${NC}"
                                last_status="downloading"
                            elif grep -q "启动 LLM 服务" "$llm_log" 2>/dev/null && [ "$last_status" != "starting" ]; then
                                printf "\r\033[K"
                                echo -e "   ${CYAN}⏳ 正在启动 vLLM 服务...${NC}"
                                last_status="starting"
                            elif grep -q "启动中" "$llm_log" 2>/dev/null && [ "$last_status" != "loading" ]; then
                                printf "\r\033[K"
                                echo -e "   ${CYAN}⏳ 正在加载模型到 GPU（这步较慢，请耐心等待）...${NC}"
                                last_status="loading"
                            fi
                        fi

                        # 显示经过时间
                        printf "\r   ${DIM}已等待 %ds...${NC}" $elapsed
                        sleep 2
                        elapsed=$((elapsed + 2))
                    done

                    # 等待命令完成
                    wait $sage_pid 2>/dev/null
                    local exit_code=$?

                    # 清除进度行
                    printf "\r\033[K"

                    # 显示关键信息（最后 10 行）
                    if [ -f "$llm_log" ]; then
                        # 过滤掉进度条行，只显示重要信息
                        grep -v "启动中 \[" "$llm_log" | tail -10
                        rm -f "$llm_log"
                    fi

                    echo ""
                    if [ $exit_code -eq 0 ]; then
                        echo -e "${GREEN}✅ LLM 服务已启动${NC}"
                        echo -e "${DIM}   API 地址: http://localhost:8901/v1${NC}"
                        echo -e "${DIM}   状态查看: sage llm status${NC}"
                        echo -e "${DIM}   停止服务: sage llm stop${NC}"
                    else
                        echo -e "${YELLOW}⚠️  LLM 服务启动可能未完全成功，请检查状态${NC}"
                        echo -e "${DIM}   状态查看: sage llm status${NC}"
                    fi
                    echo ""
                    # 询问是否运行 LLM Demo
                    echo -ne "${BOLD}是否运行 LLM Demo 体验? [y/N]: ${NC}"
                    read -r run_demo
                    if [[ "$run_demo" =~ ^[Yy] ]]; then
                        echo ""
                        run_hello_world_demo true
                    fi
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
        3)
            if [ "$mode" = "full" ] || [ "$mode" = "dev" ]; then
                echo ""
                echo -e "${INFO} 正在启动 SAGE Studio..."
                echo -e "${DIM}   这将同时启动前端界面和后端服务${NC}"
                if [ "$has_gpu" = true ]; then
                    echo -e "${DIM}   首次启动会下载 LLM 模型（可能需要 1-2 分钟）${NC}"
                    echo -e "${DIM}   ${YELLOW}注意: LLM 启动可能需要 5 分钟，如需快速启动可选择跳过${NC}"
                    echo ""
                    echo -ne "${BOLD}是否启动本地 LLM？[Y/n]: ${NC}"
                    read -r start_llm_choice
                    if [[ "$start_llm_choice" =~ ^[Nn] ]]; then
                        echo -e "${DIM}   将跳过本地 LLM 启动（可稍后使用 'sage llm serve' 启动）${NC}"
                        local no_llm_flag="--no-llm"
                    else
                        local no_llm_flag=""
                    fi
                else
                    local no_llm_flag="--no-llm"
                fi
                echo -e "${DIM}   ${YELLOW}提示: 启动过程中会显示进度信息...${NC}"
                echo ""

                if command -v sage &>/dev/null; then
                    # 将日志重定向到临时文件，同时实时显示进度
                    local studio_log="/tmp/sage_studio_start_$$.log"

                    # 启动服务（后台运行，可能带 --no-llm 参数）
                    sage studio start $no_llm_flag > "$studio_log" 2>&1 &
                    local sage_pid=$!

                    # 实时监控日志并显示关键进度
                    local elapsed=0
                    local max_wait=300  # 最多等待 5 分钟
                    local last_status=""
                    local status_shown=""

                    echo -e "${CYAN}📦 启动进度:${NC}"

                    while kill -0 $sage_pid 2>/dev/null && [ $elapsed -lt $max_wait ]; do
                        # 尝试从日志中获取当前状态
                        if [ -f "$studio_log" ]; then
                            local new_status=""

                            # 按顺序检测状态，只匹配最新的状态
                            if grep -q "依赖检查失败" "$studio_log" 2>/dev/null; then
                                new_status="failed"
                            elif grep -qE "(Studio 启动成功|Studio started successfully)" "$studio_log" 2>/dev/null; then
                                new_status="completed"
                            elif grep -qE "(检查 npm 依赖|npm install)" "$studio_log" 2>/dev/null; then
                                new_status="installing_deps"
                            elif grep -q "启动 Studio 服务" "$studio_log" 2>/dev/null; then
                                new_status="starting_frontend"
                            elif grep -qE "(LLM.*started|Gateway.*started)" "$studio_log" 2>/dev/null; then
                                new_status="llm_ready"
                            elif grep -qE "(Waiting for LLM.*to be ready|Health check URL)" "$studio_log" 2>/dev/null; then
                                new_status="waiting_llm"
                            elif grep -qE "(启动 LLM 服务|Starting LLM)" "$studio_log" 2>/dev/null; then
                                new_status="starting_llm"
                            elif grep -qE "(检测到.*GPU|检查.*Node\.js)" "$studio_log" 2>/dev/null; then
                                new_status="starting"
                            fi

                            # 只在状态改变时输出新消息
                            if [ -n "$new_status" ] && [ "$new_status" != "$last_status" ]; then
                                # 清除之前的进度指示器
                                printf "\r\033[K"

                                case "$new_status" in
                                    "starting")
                                        echo -e "   ${GREEN}✓${NC} 检查运行环境"
                                        ;;
                                    "starting_llm")
                                        echo -e "   ${CYAN}⏳${NC} 启动 LLM 服务（首次约 1-2 分钟，加载模型到 GPU）..."
                                        ;;
                                    "waiting_llm")
                                        echo -e "   ${CYAN}⏳${NC} 等待 LLM 服务就绪（最多 5 分钟）..."
                                        ;;
                                    "llm_ready")
                                        echo -e "   ${GREEN}✓${NC} LLM 服务已就绪"
                                        ;;
                                    "starting_frontend")
                                        echo -e "   ${CYAN}⏳${NC} 启动前端界面..."
                                        ;;
                                    "installing_deps")
                                        echo -e "   ${CYAN}⏳${NC} 安装前端依赖（首次约 2-3 分钟）..."
                                        ;;
                                    "completed")
                                        echo -e "   ${GREEN}✓${NC} Studio 启动成功"
                                        last_status="$new_status"
                                        break
                                        ;;
                                    "failed")
                                        echo -e "   ${RED}✗${NC} 依赖检查失败"
                                        last_status="$new_status"
                                        break
                                        ;;
                                esac

                                last_status="$new_status"
                            fi

                            # 只在长时间等待状态显示进度指示器和实时日志
                            if [ "$last_status" = "waiting_llm" ]; then
                                # 显示 LLM 日志的最新进展
                                if [ -f "$studio_log" ]; then
                                    local latest_llm_log
                                    # 提取最后一条有意义的日志（过滤掉空行和进度条）
                                    latest_llm_log=$(grep -E "(Initializing|Loading|Starting|Model loaded|vLLM)" "$studio_log" 2>/dev/null | tail -1 | cut -c1-80)
                                    if [ -n "$latest_llm_log" ]; then
                                        printf "\r   ${DIM}%s (%ds)${NC}" "$latest_llm_log" $elapsed
                                    else
                                        printf "\r   ${DIM}等待 LLM 启动... %ds${NC}" $elapsed
                                    fi
                                else
                                    printf "\r   ${DIM}等待 LLM 启动... %ds${NC}" $elapsed
                                fi
                            elif [ "$last_status" = "installing_deps" ]; then
                                printf "\r   ${DIM}安装依赖中 %ds...${NC}" $elapsed
                            fi
                        fi

                        sleep 2
                        elapsed=$((elapsed + 2))
                    done

                    # 清除进度行
                    printf "\r\033[K"

                    # 等待命令完成
                    wait $sage_pid 2>/dev/null
                    local exit_code=$?

                    # 显示最终状态
                    echo ""
                    if [ $exit_code -eq 0 ]; then
                        echo -e "${GREEN}✅ Studio 已成功启动${NC}"
                        echo -e "${DIM}   前端地址: http://localhost:5173${NC}"
                        echo -e "${DIM}   后端 API: http://localhost:8000${NC}"
                        echo -e "${DIM}   状态查看: sage studio status${NC}"
                        echo -e "${DIM}   停止服务: sage studio stop${NC}"
                        echo ""
                        echo -e "${CYAN}💡 提示: 在浏览器中打开 http://localhost:5173 开始使用 Studio${NC}"
                    else
                        echo -e "${RED}❌ Studio 启动失败${NC}"
                        echo ""
                        echo -e "${YELLOW}错误详情（最后 50 行）:${NC}"
                        if [ -f "$studio_log" ]; then
                            # 过滤出错误和警告信息
                            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                            grep -E "(❌|⚠️|ERROR|CRITICAL|依赖检查失败|Node\.js|版本)" "$studio_log" | tail -30 || tail -50 "$studio_log"
                            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                        fi
                        echo ""
                        echo -e "${YELLOW}📋 常见问题排查：${NC}"
                        echo -e "  ${BOLD}1. Node.js 版本问题${NC}"
                        echo -e "     ${DIM}检查: node --version  # 需要 v20+${NC}"
                        echo -e "     ${DIM}修复: conda install -y nodejs=22 -c conda-forge${NC}"
                        echo ""
                        echo -e "  ${BOLD}2. LLM 服务启动超时${NC}"
                        echo -e "     ${DIM}使用更小模型: sage studio start --llm-model Qwen/Qwen2.5-0.5B-Instruct${NC}"
                        echo -e "     ${DIM}或跳过 LLM: sage studio start --no-llm${NC}"
                        echo ""
                        echo -e "  ${BOLD}3. 端口被占用${NC}"
                        echo -e "     ${DIM}检查: sage studio status${NC}"
                        echo -e "     ${DIM}清理: sage studio stop${NC}"
                        echo ""
                        echo -e "${BLUE}🔍 查看完整日志：${NC}"
                        echo -e "  ${CYAN}tail -100 $studio_log${NC}"
                        echo -e "  ${CYAN}sage studio logs --follow${NC}"
                        echo ""
                        echo -e "${DIM}   状态查看: sage studio status${NC}"
                        echo -e "${DIM}   重新启动: sage studio start${NC}"
                    fi

                    # 清理日志
                    rm -f "$studio_log"
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
        4|"")
            echo ""
            echo -e "${DIM}已跳过。稍后可用以下命令:${NC}"
            echo -e "  ${CYAN}git clone https://github.com/intellistream/sage-examples.git${NC}"
            echo -e "  ${CYAN}python sage-examples/tutorials/hello_world.py${NC}  # Hello World"
            echo -e "  ${CYAN}sage llm serve${NC}                                  # LLM 服务"
            echo -e "  ${CYAN}sage studio start${NC}                               # Studio 界面"
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
        "minimal")
            echo -e "${BLUE}最小安装模式：${NC}"
            echo -e "  # 只包含 SAGE 核心包 (L1-L5)，适合容器部署和生产环境"
            echo -e "  python3 -c 'from sage.kernel import Pipeline; print(\"Pipeline ready\")'"
            echo ""
            echo -e "${BLUE}按需安装可选功能：${NC}"
            echo -e "  pip install isage-middleware[ml]         # ML 功能 (torch, transformers)"
            echo -e "  pip install isage-middleware[vdb]        # 向量数据库 (faiss)"
            echo -e "  pip install isage-middleware[streaming]  # 流处理扩展"
            echo ""
            ;;
        "dev")
            echo -e "${BLUE}开发者模式：${NC}"
            echo -e "  # 包含核心包 + 开发工具"
            echo -e "  sage-dev test                    # 运行测试"
            echo -e "  sage-dev quality                 # 代码质量检查"
            echo -e "  pre-commit run --all-files       # 运行所有检查"
            echo ""
            echo -e "${BLUE}按需安装可选功能：${NC}"
            echo -e "  pip install isage-middleware[ml,vdb]     # ML + 向量数据库"
            echo -e "  pip install isage-kernel[ml]             # Kernel ML 扩展"
            echo ""
            ;;
        "full")
            echo -e "${BLUE}完整功能模式（默认）：${NC}"
            echo -e "  # 包含所有核心功能 + 科学计算 + ML + 向量数据库"
            echo -e "  sage --help                      # 查看 CLI 命令"
            echo -e "  jupyter notebook                 # 启动 Jupyter 笔记本"
            echo -e "  sage-dev test                    # 运行测试"
            echo -e "  sage-dev quality                 # 代码质量检查"
            echo ""
            ;;
        # 兼容旧模式名称
        "core")
            echo -e "${BLUE}核心运行时模式（已改名为 minimal）：${NC}"
            echo -e "  python3 -c 'from sage.kernel import Pipeline; print(\"Pipeline ready\")'"
            echo ""
            ;;
        "standard")
            echo -e "${BLUE}标准模式（已合并到 full）：${NC}"
            echo -e "  sage --help                      # 查看 CLI 命令"
            echo ""
            ;;
    esac

    # 独立包安装提示（所有模式通用）
    echo -e "${BLUE}独立包（按需安装）：${NC}"
    echo -e "  pip install isage-benchmark             # 性能基准测试"
    echo -e "  pip install isagellm                    # LLM 推理引擎"
    echo -e "  pip install isage-edge                  # Edge 聚合器"
    echo -e "  git clone https://github.com/intellistream/sage-studio   # Web UI"
    echo -e "  git clone https://github.com/intellistream/sage-examples # 示例代码"
    echo ""

    if [ "$mode" = "dev" ] || [ "$mode" = "full" ]; then
        echo -e "${BLUE}C++扩展管理（可选）：${NC}"
        echo -e "  ${DIM}# C++扩展已在安装 sage-middleware 时自动构建${NC}"
        echo -e "  sage extensions status           # 检查扩展状态"
        echo -e "  sage extensions install --force  # 强制重新构建扩展"
        echo ""
    fi

    echo -e "${BLUE}文档和示例：${NC}"
    echo -e "  ${GRAY}https://intellistream.github.io/SAGE-Pub/${NC}"
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
    "\${workspaceFolder}/packages/sage-tools/src",
    "\${workspaceFolder}/packages/sage-cli/src"
  ]
}
EOF

    echo -e "${CHECK} 已创建 VS Code 配置: $settings_file"
    echo -e "${INFO} VS Code 现在会自动激活 conda 环境: $env_name"
    return 0
}
