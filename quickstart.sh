#!/bin/bash
# 🚀 SAGE 快速安装脚本 - 重构版本
# 模块化设计，分离关注点，便于维护

# 强制告诉 VS Code/xterm.js 支持 ANSI 和 256 色
export TERM=xterm-256color
set -e

# 获取脚本所在目录（使用 SAGE_ROOT 避免与子模块的 SCRIPT_DIR 冲突）
SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$SAGE_ROOT/tools/install"

# 自动设置 HuggingFace 镜像（国内网络加速）
# 如果用户已设置 HF_ENDPOINT 则不覆盖
if [ -z "${HF_ENDPOINT}" ]; then
    # 检测是否能直接访问 huggingface.co
    if ! curl -s --connect-timeout 3 https://huggingface.co >/dev/null 2>&1; then
        export HF_ENDPOINT="https://hf-mirror.com"
        echo -e "\033[2m自动设置 HuggingFace 镜像: $HF_ENDPOINT\033[0m"

        # 检测到国内网络，提示配置 HF_TOKEN
        if [ -z "${HF_TOKEN}" ] && [ ! -f ".env" ] || ! grep -q "HF_TOKEN=" .env 2>/dev/null; then
            echo -e "\033[33m💡 提示: 检测到您在中国大陆网络环境\033[0m"
            echo -e "\033[2m为避免 HuggingFace API 限流 (429 错误)，建议配置 HF_TOKEN\033[0m"
            echo -e "\033[2m获取 token: https://huggingface.co/settings/tokens\033[0m"
            echo ""
            read -p "是否现在配置 HF_TOKEN? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                read -p "请输入您的 HuggingFace Token: " hf_token
                if [ -n "$hf_token" ]; then
                    # 创建或更新 .env 文件
                    if [ ! -f ".env" ]; then
                        cp .env.template .env 2>/dev/null || touch .env
                    fi
                    # 添加或更新 HF_TOKEN
                    if grep -q "^HF_TOKEN=" .env 2>/dev/null; then
                        sed -i "s/^HF_TOKEN=.*/HF_TOKEN=$hf_token/" .env
                    else
                        echo "HF_TOKEN=$hf_token" >> .env
                    fi
                    # 同时添加 HF_ENDPOINT
                    if ! grep -q "^HF_ENDPOINT=" .env 2>/dev/null; then
                        echo "HF_ENDPOINT=https://hf-mirror.com" >> .env
                    fi
                    echo -e "\033[32m✅ HF_TOKEN 已保存到 .env 文件\033[0m"
                    export HF_TOKEN="$hf_token"
                fi
            else
                echo -e "\033[2m跳过 HF_TOKEN 配置（可稍后在 .env 文件中手动添加）\033[0m"
            fi
        fi
    fi
fi

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
source "$TOOLS_DIR/examination_tools/mirror_selector.sh"  # 网络加速优化（增强版）
source "$TOOLS_DIR/installation_table/main_installer.sh"
source "$TOOLS_DIR/fixes/environment_doctor.sh"
source "$TOOLS_DIR/fixes/numpy_fix.sh"
source "$TOOLS_DIR/fixes/friendly_error_handler.sh"
source "$TOOLS_DIR/fixes/checkpoint_manager.sh"

# 避免 submodule 初始化时自动拉取 Git LFS 大文件（可通过预先设置变量覆盖）
SAGE_SET_SKIP_SMUDGE=0
if [ -z "${GIT_LFS_SKIP_SMUDGE+x}" ]; then
    export GIT_LFS_SKIP_SMUDGE=1
    SAGE_SET_SKIP_SMUDGE=1
fi

# 在脚本开始时立即进行偏移探测
pre_check_system_environment

# 根据偏移探测结果设置Unicode符号
setup_unicode_symbols

# 主函数
sync_submodules_if_requested() {
    local should_sync="$1"

    if [ "$should_sync" != "true" ]; then
        return
    fi

    echo ""
    echo -e "${BLUE}🔄 同步 docs-public 子模块${NC}"
    echo -e "${DIM}提示: 仅同步 docs-public（SAGE-Pub）；其他组件已随源码或 pip 依赖提供${NC}"

    if [ ! -f "$SAGE_ROOT/manage.sh" ]; then
        echo -e "${YELLOW}⚠️  未找到 manage.sh，跳过 docs-public 同步${NC}"
        echo -e "${DIM}提示: 手动运行 ./tools/maintenance/sage-maintenance.sh submodule init${NC}"
        return
    fi

    if ! bash "$SAGE_ROOT/manage.sh"; then
        echo -e "${YELLOW}⚠️  docs-public 同步失败，请稍后手动运行 ${DIM}./manage.sh bootstrap${NC}"
        return
    fi
}

# 主函数
main() {
    # 运行日志管理
    if [ -f "$TOOLS_DIR/log_management.sh" ]; then
        bash "$TOOLS_DIR/log_management.sh" "$SAGE_ROOT/.sage/logs"
    fi

    # 解析命令行参数（包括帮助检查）
    parse_arguments "$@"

    # 检查环境医生模式
    local run_doctor=$(get_run_doctor)
    local doctor_only=$(get_doctor_only)
    local fix_environment=$(get_fix_environment)

    # 检查断点续传选项
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
            if [ "$(get_auto_confirm)" = "true" ]; then
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
            if [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" ]] && [ "$(get_auto_confirm)" != "true" ]; then
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

    # 设置智能默认值并显示提示
    set_defaults_and_show_tips

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

        # 检查是否需要安装 nvcc (检测到 GPU 但缺少 CUDA Toolkit)
        if [ "${SAGE_NEEDS_NVCC:-false}" = "true" ]; then
            echo -e "\n${YELLOW}${BOLD}⚠️  检测到 GPU 但缺少 CUDA Toolkit (nvcc 编译器)${NC}"
            echo -e "${DIM}vLLM 需要 nvcc 才能正常运行${NC}"

            if [[ -n "${CONDA_DEFAULT_ENV:-}" || -n "${CONDA_PREFIX:-}" ]]; then
                echo -e "\n${BLUE}正在自动安装 CUDA Toolkit...${NC}"
                if conda install -c conda-forge cudatoolkit-dev -y --override-channels; then
                    echo -e "${GREEN}✅ CUDA Toolkit 安装成功${NC}"
                else
                    echo -e "${YELLOW}⚠️  CUDA Toolkit 自动安装失败${NC}"
                    echo -e "${DIM}请手动安装: conda install -c conda-forge cudatoolkit-dev -y --override-channels${NC}"
                fi
            else
                echo -e "${YELLOW}未检测到 conda 环境，请手动安装 CUDA Toolkit${NC}"
                echo -e "${DIM}推荐: conda install -c conda-forge cudatoolkit-dev -y --override-channels${NC}"
            fi
        fi

        # 保持原有的 numpy 检查
        if ! precheck_numpy_environment ".sage/logs/install.log"; then
            echo -e "${YELLOW}⚠️  检测到潜在 numpy 环境问题，但将继续尝试安装${NC}"
        fi
    fi

    # 如果没有指定任何参数且不在 CI 环境中，显示交互式菜单
    if [ $# -eq 0 ] && [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" && -z "${GITLAB_CI:-}" && -z "${JENKINS_URL:-}" && -z "${BUILDKITE:-}" ]]; then
        show_installation_menu
    fi

    # 获取解析后的参数
    local mode=$(get_install_mode)
    local environment=$(get_install_environment)
    local auto_confirm=$(get_auto_confirm)
    local clean_cache=$(get_clean_pip_cache)
    local sync_submodules=$(get_sync_submodules)
    local verify_deps=$(get_verify_deps)
    local verify_deps_strict=$(get_verify_deps_strict)
    local skip_hooks=$(should_skip_hooks)
    local hooks_mode=$(get_hooks_mode_value)
    local hooks_profile=$(get_hooks_profile_value)
    local use_mirror=$(should_use_pip_mirror)
    local mirror_source=$(get_mirror_source_value)
    local clean_before_install=$(get_clean_before_install)
    local install_vllm=$(should_install_vllm)
    local vllm_from_source=$(should_install_vllm_from_source)

    # 导出 pip 镜像配置为环境变量，供子脚本使用
    export USE_PIP_MIRROR="$use_mirror"
    export MIRROR_SOURCE="$mirror_source"
    # 导出 vLLM 源码安装配置
    export SAGE_VLLM_FROM_SOURCE="$vllm_from_source"

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

        if [[ ! "$continue_choice" =~ ^[Yy]$ ]] && [[ ! -z "$continue_choice" ]]; then
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

    sync_submodules_if_requested "$sync_submodules"

    # 生成子模块标记文件（首次安装或更新时）
    # 注意：已禁用以避免在安装后产生未提交的更改（见 issue #1097）
    # 用户可以手动运行 tools/git-tools/generate-submodule-markers.sh 来生成这些文件
    # if [ "$sync_submodules" = "true" ] && [ -f "$SAGE_ROOT/tools/git-tools/generate-submodule-markers.sh" ]; then
    #     echo ""
    #     echo -e "${INFO} 生成子模块标记文件..."
    #     if bash "$SAGE_ROOT/tools/git-tools/generate-submodule-markers.sh" >/dev/null 2>&1; then
    #         echo -e "${GREEN}   ✅ 子模块标记文件已生成${NC}"
    #     else
    #         echo -e "${DIM}   ℹ️  子模块标记文件生成跳过${NC}"
    #     fi
    # fi

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
    install_sage "$mode" "$environment" "$clean_cache" "$install_vllm"

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

            # 1. 安装 pre-commit 框架（代码质量）
            if command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1; then
                echo -e "${DIM}   安装 pre-commit 框架...${NC}"
                if pip install -q pre-commit 2>/dev/null || pip3 install -q pre-commit 2>/dev/null; then
                    echo -e "${GREEN}   ✅ pre-commit 框架已安装${NC}"
                else
                    echo -e "${YELLOW}   ⚠️  pre-commit 安装失败，代码格式检查将被跳过${NC}"
                fi
            fi

            # 2. 安装 Git hooks（使用新的 sage-dev maintain hooks 命令）
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
                echo -e "${YELLOW}⚠️  sage-dev 命令不可用，跳过 Git hooks 安装${NC}"
                echo -e "${DIM}   安装完成后激活环境并运行: sage-dev maintain hooks install${NC}"
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

            # 安装主仓库的 pre-commit hooks
            if command -v pre-commit >/dev/null 2>&1; then
                echo -e "${DIM}   配置主仓库 pre-commit hooks...${NC}"
                if pre-commit install 2>/dev/null; then
                    echo -e "${GREEN}   ✅ 主仓库 pre-commit hooks 已安装${NC}"
                else
                    echo -e "${YELLOW}   ⚠️  主仓库 pre-commit hooks 安装失败${NC}"
                fi
            else
                echo -e "${YELLOW}   ⚠️  pre-commit 未安装，跳过 Git hooks 安装${NC}"
            fi

            # 安装所有子模块的 pre-commit hooks
            if command -v pre-commit >/dev/null 2>&1; then
                echo -e "${DIM}   配置子模块 pre-commit hooks...${NC}"
                local submodules_with_hooks=0
                local submodules_installed=0

                # 定义所有子模块路径
                # 注意: C++ 扩展已迁移为独立 PyPI 包 (isagevdb, isage-flow, isage-tsdb, neuromem, isage-refiner)
                # sageLLM 已独立为私有仓库
                local submodule_paths=(
                    # 所有子模块已迁移或独立，不在此列表中
                )

                for submodule_path in "${submodule_paths[@]}"; do
                    local full_path="$SAGE_ROOT/$submodule_path"
                    local submodule_name=$(basename "$submodule_path")

                    if [ -d "$full_path" ] && [ -f "$full_path/.pre-commit-config.yaml" ]; then
                        ((submodules_with_hooks++)) || true
                        if (cd "$full_path" && pre-commit install 2>/dev/null); then
                            echo -e "${GREEN}   ✅ $submodule_name pre-commit hooks 已安装${NC}"
                            ((submodules_installed++)) || true
                        else
                            echo -e "${DIM}   ℹ️  $submodule_name pre-commit hooks 安装跳过${NC}"
                        fi
                    fi
                done

                # 使用 || true 避免 set -e 导致脚本退出
                if [ $submodules_with_hooks -gt 0 ]; then
                    echo -e "${GREEN}   ✅ 子模块 pre-commit hooks: $submodules_installed/$submodules_with_hooks 安装成功${NC}"
                else
                    echo -e "${DIM}   ℹ️  未发现子模块 pre-commit 配置${NC}"
                fi || true
            else
                echo -e "${YELLOW}   ⚠️  pre-commit 未安装，跳过子模块 hooks${NC}"
            fi
        fi

        show_usage_tips "$mode"

        # 显示快速启动服务菜单（交互模式）
        # 注意：已由 show_usage_tips 内部调用 prompt_start_llm_service
        # if [ "$(get_auto_confirm)" != "true" ] && [ -z "${CI:-}" ] && [ -z "${GITHUB_ACTIONS:-}" ]; then
        #     echo ""
        #     prompt_start_llm_service "$mode"
        # fi

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
        # 使用适配的居中显示函数，确保在所有环境下都能正确居中
        if [ "$VSCODE_OFFSET_ENABLED" = true ]; then
            center_text_formatted "${ROCKET} 欢迎使用 SAGE！${ROCKET}" "$GREEN$BOLD"
        else
            center_text "${ROCKET} 欢迎使用 SAGE！${ROCKET}" "$GREEN$BOLD"
        fi
        echo ""

        if [ "$SAGE_SET_SKIP_SMUDGE" = 1 ]; then
            echo -e "${DIM}提示: 已跳过 Git LFS 大文件的自动下载，以缩短初始化时间。${NC}"
            echo -e "${DIM}如需使用 LibAMM 基准数据，请手动执行:${NC}"
            echo -e "  ${DIM}cd packages/sage-benchmark/src/sage/data && git lfs pull${NC}"
            echo -e "  ${DIM}cd ../benchmark/benchmark_amm && bash tools/setup_data.sh${NC}"
        fi
    else
        echo ""
        echo -e "${YELLOW}安装可能成功，请手动验证：${NC}"
        # 使用正确的 Python 命令
        local python_cmd="${PYTHON_CMD:-python3}"
        echo -e "  $python_cmd -c \"import sage; print(sage.__version__)\""
    fi
}

# 运行主函数
main "$@"
