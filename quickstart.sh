#!/bin/bash
# 🚀 SAGE 快速安装脚本 - 重构版本
# 模块化设计，分离关注点，便于维护

# 强制告诉 VS Code/xterm.js 支持 ANSI 和 256 色
export TERM=xterm-256color
set -e

# 获取脚本所在目录（使用 SAGE_ROOT 避免与子模块的 SCRIPT_DIR 冲突）
SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$SAGE_ROOT/tools/install"

# 统一 Python/pip 命令，避免 pip 指向用户级路径导致安装到错误环境
export PYTHON_CMD="${PYTHON_CMD:-python3}"
export PIP_CMD="${PIP_CMD:-$PYTHON_CMD -m pip}"

# 导入所有模块
source "$TOOLS_DIR/display_tools/colors.sh"
source "$TOOLS_DIR/display_tools/output_formatter.sh"
source "$TOOLS_DIR/display_tools/interface.sh"
source "$TOOLS_DIR/examination_tools/system_check.sh"
source "$TOOLS_DIR/examination_tools/system_deps.sh"
source "$TOOLS_DIR/examination_tools/comprehensive_check.sh"
source "$TOOLS_DIR/examination_tools/environment_prechecks.sh"
source "$TOOLS_DIR/examination_tools/install_verification.sh"
source "$TOOLS_DIR/download_tools/argument_parser.sh"
source "$TOOLS_DIR/download_tools/clone_satellite_repos.sh"
source "$TOOLS_DIR/examination_tools/mirror_selector.sh"  # 网络加速优化（增强版）
source "$TOOLS_DIR/installation_table/main_installer.sh"
source "$TOOLS_DIR/fixes/environment_doctor.sh"
source "$TOOLS_DIR/fixes/numpy_fix.sh"
source "$TOOLS_DIR/fixes/friendly_error_handler.sh"
source "$TOOLS_DIR/fixes/checkpoint_manager.sh"

# 在脚本开始时立即进行偏移探测
pre_check_system_environment

# 根据偏移探测结果设置Unicode符号
setup_unicode_symbols

is_interactive_session() {
    [ -t 0 ] && [ -t 1 ]
}

# 在参数解析后再处理 HF 配置，避免 --yes/CI 模式被提前交互阻塞
configure_huggingface_network() {
    local auto_confirm="$1"

    if [ -n "${HF_ENDPOINT:-}" ]; then
        return 0
    fi

    if curl -s --connect-timeout 3 https://huggingface.co >/dev/null 2>&1; then
        return 0
    fi

    export HF_ENDPOINT="https://hf-mirror.com"
    echo -e "${DIM}自动设置 HuggingFace 镜像: $HF_ENDPOINT${NC}"

    if [ -n "${HF_TOKEN:-}" ]; then
        return 0
    fi

    local has_env_token=false
    if [ -f ".env" ] && grep -q "^HF_TOKEN=" .env 2>/dev/null; then
        has_env_token=true
    fi
    if [ "$has_env_token" = true ]; then
        return 0
    fi

    if [ "$auto_confirm" = "true" ] || [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" ]] || ! is_interactive_session; then
        echo -e "${YELLOW}💡 检测到可能受限网络，建议在 .env 中配置 HF_TOKEN 以减少 429 频率${NC}"
        return 0
    fi

    echo -e "${YELLOW}💡 提示: 检测到受限网络环境${NC}"
    echo -e "${DIM}为避免 HuggingFace API 限流 (429 错误)，建议配置 HF_TOKEN${NC}"
    echo -e "${DIM}获取 token: https://huggingface.co/settings/tokens${NC}"
    echo ""
    read -r -p "是否现在配置 HF_TOKEN? (y/N): " -n 1 reply
    echo

    if [[ ! "$reply" =~ ^[Yy]$ ]]; then
        echo -e "${DIM}跳过 HF_TOKEN 配置（可稍后在 .env 文件中手动添加）${NC}"
        return 0
    fi

    read -r -p "请输入您的 HuggingFace Token: " hf_token
    if [ -z "$hf_token" ]; then
        return 0
    fi

    if [ ! -f ".env" ]; then
        cp .env.template .env 2>/dev/null || touch .env
    fi

    if grep -q "^HF_TOKEN=" .env 2>/dev/null; then
        sed -i "s/^HF_TOKEN=.*/HF_TOKEN=$hf_token/" .env
    else
        echo "HF_TOKEN=$hf_token" >> .env
    fi

    if ! grep -q "^HF_ENDPOINT=" .env 2>/dev/null; then
        echo "HF_ENDPOINT=https://hf-mirror.com" >> .env
    fi

    export HF_TOKEN="$hf_token"
    echo -e "${GREEN}✅ HF_TOKEN 已保存到 .env 文件${NC}"
}

# ─── SAGE 工作区初始化函数 ───────────────────────────────────────────────────
# 用于将所有独立 SAGE 子仓库 clone 到本地工作区目录。
# 使用方法：./quickstart.sh --workspace [--dir <path>]
_init_sage_workspace() {
    # 解析 --dir 参数
    local workspace_dir="$HOME/sage-workspace"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dir) workspace_dir="$2"; shift 2 ;;
            --dir=*) workspace_dir="${1#--dir=}"; shift ;;
            *) shift ;;
        esac
    done

    local GREEN='\033[0;32m'; local CYAN='\033[0;36m'
    local YELLOW='\033[1;33m'; local NC='\033[0m'; local BOLD='\033[1m'

    echo -e "\n${BOLD}🚀 SAGE 工作区初始化${NC}"
    echo -e "${CYAN}目标目录: ${workspace_dir}${NC}\n"

    # ── 独立子仓库列表（按层级 L1→L5）────────────────────────────────────────
    local SAGE_REPOS=(
        "intellistream/sage-common"        # L1
        "intellistream/sage-platform"      # L2
        "intellistream/sage-kernel"        # L3
        "intellistream/sage-libs"          # L3
        "intellistream/sage-middleware"    # L4
        "intellistream/sage-cli"           # L5
        "intellistream/sage-dev-tools"     # dev tooling
        "intellistream/sage-examples"      # examples
    )

    mkdir -p "$workspace_dir"

    local ok=0; local skip=0; local fail=0
    for repo in "${SAGE_REPOS[@]}"; do
        local name="${repo#*/}"
        local target="$workspace_dir/$name"
        if [ -d "$target/.git" ]; then
            echo -e "  ${YELLOW}↻${NC} $name — 已存在，正在 pull..."
            git -C "$target" pull --ff-only 2>&1 | tail -1 && ((skip++)) || ((fail++))
        else
            echo -e "  ${CYAN}⬇${NC} clone $repo..."
            if git clone "https://github.com/$repo.git" "$target" --depth 1 2>&1 | tail -1; then
                ((ok++))
            else
                echo -e "  ${YELLOW}⚠ clone 失败，跳过 $name${NC}"
                ((fail++))
            fi
        fi
    done

    # ── 主 SAGE meta 仓库（当前仓库）─────────────────────────────────────────
    if [ ! -d "$workspace_dir/SAGE/.git" ]; then
        echo -e "  ${CYAN}⬇${NC} clone intellistream/SAGE (meta)..."
        git clone "https://github.com/intellistream/SAGE.git" "$workspace_dir/SAGE" --depth 1 2>&1 | tail -1 && ((ok++)) || ((fail++))
    else
        echo -e "  ${YELLOW}↻${NC} SAGE — 已存在，跳过"
        ((skip++))
    fi

    echo ""
    echo -e "${GREEN}✓ 完成: ${ok} 新克隆, ${skip} 已存在, ${fail} 失败${NC}"
    echo -e "\n${BOLD}下一步:${NC}"
    echo -e "  cd $workspace_dir/<repo>"
    echo -e "  ./quickstart.sh --dev --yes    # 安装 editable dev 依赖"
    echo -e "\n  或安装 meta 包（仅依赖已发布版本）:"
    echo -e "  pip install \"isage[dev]\"\n"
    return $fail
}

# 主函数
main() {
    # ── 工作区引导模式 (--workspace) ─────────────────────────────────────────
    # Clone 所有 SAGE 子仓库到 WORKSPACE_DIR（默认 $HOME/sage-workspace）。
    # 这是新开发者快速设置完整生态系统开发环境的推荐方式。
    if [[ " $* " == *" --workspace "* ]] || [[ " $* " == *" --init-workspace "* ]]; then
        _init_sage_workspace "$@"
        exit $?
    fi

    # 运行日志管理
    if [ -f "$TOOLS_DIR/log_management.sh" ]; then
        bash "$TOOLS_DIR/log_management.sh" "$SAGE_ROOT/.sage/logs"
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🚀 SAGE Quickstart Pipeline${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Phase 1: 参数解析（含默认值设置）
    parse_arguments "$@"

    # 解析完成后再处理 HF 网络配置，避免 --yes/CI 触发早期交互
    local auto_confirm=$(get_auto_confirm)
    configure_huggingface_network "$auto_confirm"

    # Phase 2: 诊断与断点控制
    local run_doctor=$(get_run_doctor)
    local doctor_only=$(get_doctor_only)
    local fix_environment=$(get_fix_environment)
    local resume_install=$(get_resume_install)
    local reset_checkpoint=$(get_reset_checkpoint)

    # 处理检查点系统
    if [ "$reset_checkpoint" = "true" ]; then
        echo -e "${YELLOW}🔄 重置安装进度...${NC}"
        reset_checkpoint
    fi

    # 初始化检查点系统
    init_checkpoint_system

    # 处理断点续传
    if [ "$resume_install" = "true" ] || can_resume_install; then
        if show_resume_options; then
            echo -e "${INFO} 从断点继续安装..."
        fi
    fi

    if [ "$run_doctor" = "true" ]; then
        # 导入环境医生功能
        if [ -f "$TOOLS_DIR/fixes/environment_doctor.sh" ]; then
            source "$TOOLS_DIR/fixes/environment_doctor.sh"

            # 确保如果使用了 --yes 参数，环境医生也会自动确认修复
            if [ "$auto_confirm" = "true" ]; then
                export AUTO_CONFIRM_FIX="true"
            fi

            local fix_result=0  # 初始化变量

            if [ "$fix_environment" = "true" ]; then
                run_full_diagnosis || true
                run_auto_fixes
                fix_result=$?
            else
                # 如果诊断发现问题，自动提示修复
                if ! run_full_diagnosis; then
                    echo ""
                    run_auto_fixes
                    fix_result=$?
                else
                    fix_result=0
                fi
            fi

            # 检查是否需要重启 shell（退出码 42）
            if [ "$fix_result" -eq 42 ]; then
                echo ""
                exit 0
            fi

            if [ "$doctor_only" = "true" ]; then
                exit $fix_result
            fi

            # 诊断完成，询问是否继续安装（CI 环境自动确认）
            echo ""
            if [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" ]] && [ "$auto_confirm" != "true" ]; then
                echo -e "${BLUE}${BOLD}📋 环境诊断完成${NC}"
                echo -e "${DIM}诊断结果已显示在上方${NC}"
                echo ""
                read -p "是否继续进行 SAGE 安装？[Y/n] " -r response
                response=${response,,}
                if [[ "$response" =~ ^(n|no)$ ]]; then
                    echo -e "${YELLOW}安装已取消${NC}"
                    exit 0
                fi
                echo ""
            else
                echo -e "${INFO} CI 环境或自动确认模式，继续安装..."
                echo ""
            fi
        else
            echo -e "${RED}错误：环境医生模块未找到${NC}"
            exit 1
        fi
    fi

    # 显示欢迎界面
    show_welcome

    # 环境预检查（除非在医生模式中）
    if [ "$run_doctor" != "true" ]; then
        echo -e "\n${BLUE}🔍 安装前环境检查${NC}"

        # 确保.sage目录存在
        mkdir -p .sage/logs

        # 运行新的环境预检查 - 启用 CUDA 检查
        local skip_cuda="false"

        if ! run_environment_prechecks "$skip_cuda" ".sage/logs/environment_precheck.log"; then
            echo -e "${YELLOW}⚠️  环境预检查发现问题，但将继续尝试安装${NC}"
            echo -e "${DIM}提示: 查看详细报告 .sage/logs/environment_precheck.log${NC}"
        fi

        # 保持原有的 numpy 检查
        if ! precheck_numpy_environment ".sage/logs/install.log"; then
            echo -e "${YELLOW}⚠️  检测到潜在 numpy 环境问题，但将继续尝试安装${NC}"
        fi
    fi
    # Phase 3: 交互式菜单（仅在无参数且非 CI）
    if [ $# -eq 0 ] && [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" && -z "${GITLAB_CI:-}" && -z "${JENKINS_URL:-}" && -z "${BUILDKITE:-}" ]]; then
        show_installation_menu
        auto_confirm=$(get_auto_confirm)
    fi

    # Phase 4: 读取最终安装配置
    local mode=$(get_install_mode)
    local environment=$(get_install_environment)
    local clone_satellites=$(should_clone_satellite_repos)
    export SAGE_INSTALL_MODE="$mode"
    export SAGE_AUTO_CONFIRM="$auto_confirm"
    local clean_cache=$(get_clean_pip_cache)
    local verify_deps=$(get_verify_deps)
    local verify_deps_strict=$(get_verify_deps_strict)
    local skip_hooks=$(should_skip_hooks)
    local hooks_mode=$(get_hooks_mode_value)
    local hooks_profile=$(get_hooks_profile_value)
    local use_mirror=$(should_use_pip_mirror)
    local mirror_source=$(get_mirror_source_value)
    local clean_before_install=$(get_clean_before_install)
    export CLEAN_BEFORE_INSTALL="$clean_before_install"

    # 导出 pip 镜像配置为环境变量，供子脚本使用
    export USE_PIP_MIRROR="$use_mirror"
    export MIRROR_SOURCE="$mirror_source"

    # 执行安装前清理（如果启用）
    if [ "$clean_before_install" = "true" ]; then
        echo ""
        echo -e "${BLUE}🧹 执行安装前清理...${NC}"
        if [ -f "$SAGE_ROOT/tools/maintenance/helpers/pre_install_cleanup.sh" ]; then
            bash "$SAGE_ROOT/tools/maintenance/helpers/pre_install_cleanup.sh"
        else
            echo -e "${YELLOW}⚠️  清理脚本未找到，跳过清理${NC}"
        fi
    fi

    # 应用网络加速优化（在安装前配置）
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🚀 网络下载优化${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 智能配置 pip（自动检测网络 + 镜像选择 + 并行优化）
    smart_configure_pip "true" "true"

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 如果不是自动确认模式，显示最终确认
    if [ "$auto_confirm" != "true" ]; then
        echo ""
        echo -e "${BLUE}📋 最终安装配置：${NC}"
        show_install_configuration

        echo -e "${YELLOW}确认开始安装吗？${NC} [${GREEN}Y${NC}/${RED}n${NC}]"
        read -p "请输入选择: " -r continue_choice
        # Trim whitespace/control chars, then only cancel on explicit n/N
        continue_choice="${continue_choice//[[:space:]]/}"

        if [[ "$continue_choice" =~ ^[Nn] ]]; then
            echo ""
            echo -e "${INFO} 安装已取消。"
            echo -e "${DIM}提示: 可使用 ./quickstart.sh --help 查看所有选项${NC}"
            echo -e "${DIM}提示: 使用 --yes 参数可跳过此确认步骤${NC}"
            exit 0
        fi
    else
        echo ""
        echo -e "${INFO} 使用自动确认模式，直接开始安装..."
        show_install_configuration
    fi

    # 切换到项目根目录
    cd "$SAGE_ROOT"

    # dev 模式下自动克隆附属仓库（默认启用，可用 --no-clone-satellites 关闭）
    if [ "$mode" = "dev" ] && [ "$clone_satellites" = "true" ]; then
        echo ""
        echo -e "${BLUE}📚 同步附属仓库（dev 模式）...${NC}"
        clone_all_public_repos "$(dirname "$SAGE_ROOT")" "$SAGE_ROOT/SAGE.code-workspace" || true
    fi

    # 执行深度依赖验证（如果指定了 --verify-deps）
    if [ "$verify_deps" = "true" ]; then
        echo ""
        echo -e "${BLUE}🔐 执行深度依赖验证...${NC}"

        # 加载验证模块
        if [ -f "$TOOLS_DIR/examination_tools/dependency_verification.sh" ]; then
            source "$TOOLS_DIR/examination_tools/dependency_verification.sh"

            # 执行深度验证
            if perform_deep_verification "requirements.txt" ".sage" "$verify_deps_strict"; then
                echo -e "${CHECK} ✅ 深度验证通过"
            else
                if [ "$verify_deps_strict" = "true" ]; then
                    echo -e "${CROSS} ❌ 严格验证失败，中止安装"
                    exit 1
                else
                    echo -e "${WARNING} ⚠️  验证发现问题，但继续进行安装"
                fi
            fi
        else
            echo -e "${YELLOW}⚠️  验证模块未找到，跳过深度验证${NC}"
        fi
        echo ""
    fi

    # 执行安装
    install_sage "$mode" "$environment" "$clean_cache"

    # 验证安装
    if run_comprehensive_verification; then
        # C++扩展已在 sage-middleware 安装时自动构建和验证
        if [ "$mode" = "standard" ] || [ "$mode" = "dev" ]; then
            echo -e "${DIM}C++扩展已通过 sage-middleware 自动构建和验证${NC}"
        fi

        # 自动安装代码质量和架构检查 Git hooks（所有模式）
        if [ "$skip_hooks" = "true" ]; then
            echo ""
            echo -e "${INFO} 跳过 Git hooks 安装（使用 --skip-hooks 选项）"
            echo -e "${DIM}   可稍后手动运行: sage-dev maintain hooks install${NC}"
        else
            echo ""
            echo -e "${INFO} 安装代码质量和架构检查工具..."

            # 安装 Git hooks（统一使用 sage-dev maintain hooks 命令）
            # 使用正确环境中的 sage-dev
            local sage_dev_cmd="sage-dev"
            if [ -n "$SAGE_ENV_NAME" ]; then
                # 如果使用 conda 环境，使用 conda run 确保在正确的环境中运行
                sage_dev_cmd="conda run -n $SAGE_ENV_NAME sage-dev"
            elif [ -x "$HOME/.local/bin/sage-dev" ]; then
                # pip 安装模式：使用 ~/.local/bin 中的 sage-dev
                sage_dev_cmd="$HOME/.local/bin/sage-dev"
            fi

            # 检查 sage-dev 是否可用
            if { [ -n "$SAGE_ENV_NAME" ] && conda run -n "$SAGE_ENV_NAME" which sage-dev >/dev/null 2>&1; } || \
               { [ -z "$SAGE_ENV_NAME" ] && command -v sage-dev >/dev/null 2>&1; } || \
               { [ -z "$SAGE_ENV_NAME" ] && [ -x "$HOME/.local/bin/sage-dev" ]; }; then
                # 确定是否后台运行
                local run_background=false
                if [ "$hooks_mode" = "background" ]; then
                    run_background=true
                elif [ "$hooks_mode" = "auto" ] && [ "$auto_confirm" != "true" ]; then
                    # 交互式安装时默认后台
                    run_background=true
                fi

                local hooks_cmd="$sage_dev_cmd maintain hooks install --mode=$hooks_profile --quiet"
                echo -e "${DIM}   配置 Git hooks（代码质量检查）...${NC}"
                if [ "$run_background" = "true" ]; then
                    echo -e "${YELLOW}   ⏳ 后台安装 hooks（首次可能需要 5-10 分钟下载工具链）...${NC}"
                    echo -e "${DIM}   （ruff, mypy, shellcheck, mdformat 等工具）${NC}"
                    # 后台运行
                    nohup $hooks_cmd >/dev/null 2>&1 &
                    echo -e "${GREEN}✅ Git hooks 后台安装已启动${NC}"
                    echo -e "${DIM}   • 代码质量检查: black, isort, ruff 等${NC}"
                    echo -e "${DIM}   • 架构合规性: 包依赖、导入路径等${NC}"
                    echo -e "${DIM}   • 跳过检查: git commit --no-verify${NC}"
                    echo -e "${DIM}   • 查看状态: sage-dev maintain hooks status${NC}"
                else
                    echo -e "${YELLOW}   ⏳ 安装 hooks（首次可能需要 5-10 分钟下载工具链）...${NC}"
                    echo -e "${DIM}   （ruff, mypy, shellcheck, mdformat 等工具）${NC}"
                    # 同步运行
                    if $hooks_cmd 2>&1; then
                        echo -e "${GREEN}✅ Git hooks 已安装${NC}"
                        echo -e "${DIM}   • 代码质量检查: black, isort, ruff 等${NC}"
                        echo -e "${DIM}   • 架构合规性: 包依赖、导入路径等${NC}"
                        echo -e "${DIM}   • 跳过检查: git commit --no-verify${NC}"

                        # 检查工具版本一致性
                        if [ -f "$SAGE_ROOT/tools/install/diagnostics/check_tool_versions.sh" ]; then
                            echo ""
                            if ! bash "$SAGE_ROOT/tools/install/diagnostics/check_tool_versions.sh" --quiet 2>/dev/null; then
                                echo -e "${YELLOW}⚠️  检测到工具版本不一致${NC}"
                                echo -e "${DIM}   运行 ./tools/install/diagnostics/check_tool_versions.sh --fix 自动修复${NC}"
                            fi
                        fi
                    else
                        echo -e "${YELLOW}⚠️  Git hooks 安装失败（可能不在 Git 仓库中）${NC}"
                        echo -e "${DIM}   可稍后手动运行: sage-dev maintain hooks install${NC}"
                    fi
                fi
            else
                echo -e "${YELLOW}⚠️  sage-dev 命令暂不可用，尝试使用 pre-commit 回退安装 hooks...${NC}"

                # 回退路径：仅安装 hooks，不负责安装依赖
                local precommit_available=false
                local precommit_cmd=""

                if command -v pre-commit >/dev/null 2>&1; then
                    precommit_available=true
                    precommit_cmd="pre-commit"
                elif [ -n "$SAGE_ENV_NAME" ] && conda run -n "$SAGE_ENV_NAME" python -c "import pre_commit" >/dev/null 2>&1; then
                    precommit_available=true
                    precommit_cmd="conda run -n $SAGE_ENV_NAME python -m pre_commit"
                elif python3 -c "import pre_commit" >/dev/null 2>&1; then
                    precommit_available=true
                    precommit_cmd="python3 -m pre_commit"
                fi

                if [ "$precommit_available" = true ] && [ -d ".git" ]; then
                    echo -e "${DIM}   使用 pre-commit 回退安装 hooks...${NC}"
                    if eval "$precommit_cmd install --config tools/config/pre-commit-config.yaml" 2>&1; then
                        echo -e "${GREEN}✅ Git hooks 已安装（pre-commit 回退路径）${NC}"
                    else
                        echo -e "${YELLOW}⚠️  pre-commit 回退安装失败${NC}"
                        echo -e "${DIM}   请激活环境后运行: sage-dev maintain hooks install${NC}"
                    fi
                else
                    echo -e "${YELLOW}⚠️  pre-commit 也不可用，跳过 Git hooks 安装${NC}"
                    echo -e "${DIM}   请激活环境后运行: sage-dev maintain hooks install${NC}"
                fi
            fi
        fi

        # 开发模式下额外设置 Git hooks（用于 submodule 管理）
        if [ "$mode" = "dev" ]; then
            echo ""
            echo -e "${INFO} 设置额外的 Git hooks（开发模式）..."
            if [ -f "$SAGE_ROOT/tools/maintenance/setup_hooks.sh" ]; then
                bash "$SAGE_ROOT/tools/maintenance/setup_hooks.sh" --all --force 2>/dev/null || {
                    echo -e "${DIM}  ℹ️  开发模式 hooks 设置跳过（非 Git 仓库或权限问题）${NC}"
                }
            fi

            # 配置 Git 设置
            echo -e "${DIM}   配置 Git 设置（rename limit, submodules）...${NC}"
            if [ -x "$SAGE_ROOT/tools/git-tools/configure-git.sh" ]; then
                if "$SAGE_ROOT/tools/git-tools/configure-git.sh" >/dev/null 2>&1; then
                    echo -e "${GREEN}   ✅ Git 配置完成${NC}"
                else
                    echo -e "${YELLOW}   ⚠️  Git 配置失败，但不影响使用${NC}"
                fi
            else
                echo -e "${DIM}   ℹ️  Git 配置脚本不存在，跳过${NC}"
            fi

            echo -e "${DIM}   ℹ️  hooks 已由 sage-dev maintain hooks install 统一管理${NC}"
        fi

        show_usage_tips "$mode"

        # 显示安装后使用提示（不自动启动服务）

        # 检查并修复依赖冲突
        echo ""
        echo -e "${INFO} 检查依赖版本兼容性..."
        if [ -f "$SAGE_ROOT/tools/install/diagnostics/check_and_fix_dependencies.sh" ]; then
            # 非交互模式检查（在 CI 环境中或自动确认模式）
            if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ "$(get_auto_confirm)" = "true" ]; then
                source "$SAGE_ROOT/tools/install/diagnostics/check_and_fix_dependencies.sh"
                check_and_fix_dependencies --non-interactive || {
                    echo -e "${DIM}  ⚠️  依赖检查完成（可能存在警告）${NC}"
                }
            else
                # 交互模式检查
                source "$SAGE_ROOT/tools/install/diagnostics/check_and_fix_dependencies.sh"
                check_and_fix_dependencies || {
                    echo -e "${DIM}  ℹ️  依赖检查跳过或失败（非关键）${NC}"
                }
            fi
        fi

        echo ""
        # ── 安装后快速健康检查 ──────────────────────────────────────────────
        echo -e "${INFO} 运行安装后健康检查..."
        local python_cmd="${PYTHON_CMD:-python3}"
        local sage_cli_ok=false
        if $python_cmd -c "import sage.cli" &>/dev/null 2>&1; then
            sage_cli_ok=true
        fi

        if [ "$sage_cli_ok" = true ]; then
            # 用 sage doctor 做层级检查（静默失败，不阻塞安装）
            if $python_cmd -m sage.cli.main doctor check 2>/dev/null; then
                :
            else
                echo -e "${DIM}  💡 可运行 [sage doctor] 查看详细诊断${NC}"
            fi
        else
            # 回退到简单 import 检查
            if $python_cmd -c "import sage.common; print('✅ sage.common', sage.common.__version__)" 2>/dev/null; then
                echo -e "${GREEN}  ✅ 核心包验证通过${NC}"
            else
                echo -e "${YELLOW}  ⚠️  core import 检查失败，请运行: sage doctor${NC}"
            fi
        fi

        echo ""
        # 使用适配的居中显示函数，确保在所有环境下都能正确居中
        if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
            center_text_formatted "${ROCKET} 欢迎使用 SAGE！${ROCKET}" "$GREEN$BOLD"
        else
            center_text "${ROCKET} 欢迎使用 SAGE！${ROCKET}" "$GREEN$BOLD"
        fi
        echo ""
        echo -e "${DIM}  💡 验证安装: [bold]sage doctor[/bold] | 快速体验: [bold]sage demo hello[/bold]${NC}"
        echo ""

        if [ "${SAGE_SET_SKIP_SMUDGE:-0}" = 1 ]; then
            echo -e "${DIM}提示: 已跳过 Git LFS 大文件的自动下载，以缩短初始化时间。${NC}"
            echo -e "${DIM}如需使用 LibAMM 基准数据，请手动执行:${NC}"
            echo -e "  ${DIM}cd packages/sage-benchmark/src/sage/data && git lfs pull${NC}"
            echo -e "  ${DIM}cd ../benchmark/benchmark_amm && bash tools/setup_data.sh${NC}"
        fi
    else
        echo ""
        echo -e "${YELLOW}安装可能成功，请手动验证：${NC}"
        local python_cmd="${PYTHON_CMD:-python3}"
        echo -e "  sage doctor           ${DIM}# 完整诊断（推荐）${NC}"
        echo -e "  $python_cmd -c \"import sage.common; print(sage.common.__version__)\"  ${DIM}# 快速验证${NC}"
    fi
}

# 运行主函数
main "$@"
