#!/bin/bash
# SAGE 安装脚本 - VLLM 安装模块
# 简化版本：直接调用现有的 vllm_local_serve.sh 进行安装

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# VLLM 安装函数
install_vllm_packages() {
    echo ""
    echo -e "${GEAR} 准备 VLLM 环境..."
    log_info "开始准备 VLLM 环境" "VLLM"

    # 检查是否在 conda 环境中
    if [[ "$CONDA_DEFAULT_ENV" != "" ]] && [[ "$CONDA_DEFAULT_ENV" != "base" ]]; then
        log_info "检测到 conda 环境: $CONDA_DEFAULT_ENV" "VLLM"
        echo -e "${INFO} 检测到 conda 环境: $CONDA_DEFAULT_ENV"
    else
        log_warn "建议在 conda 环境中使用 VLLM" "VLLM"
        echo -e "${WARNING} 建议在 conda 环境中使用 VLLM"
    fi

    # 检测并安装 vLLM
    if command -v vllm >/dev/null 2>&1; then
        log_info "VLLM 已安装" "VLLM"
        echo -e "${CHECK} VLLM 已安装"
    else
        log_info "正在安装 VLLM..." "VLLM"
        echo -e "${INFO} 正在安装 VLLM..."

        # 直接使用 pip 安装 VLLM
        if [[ "$CONDA_DEFAULT_ENV" != "" ]] && [[ "$CONDA_DEFAULT_ENV" != "base" ]]; then
            log_info "在 conda 环境 '$CONDA_DEFAULT_ENV' 中使用 pip 安装 VLLM..." "VLLM"
            echo -e "${INFO} 在 conda 环境 '$CONDA_DEFAULT_ENV' 中使用 pip 安装 VLLM..."

            if log_command "VLLM" "Install" "conda run -n \"$CONDA_DEFAULT_ENV\" pip install vllm"; then
                log_info "VLLM 安装成功！" "VLLM"
                echo -e "${CHECK} VLLM 安装成功！"
            else
                log_error "VLLM 安装失败，将在首次使用时重试" "VLLM"
                echo -e "${CROSS} VLLM 安装失败，将在首次使用时重试"
            fi
        else
            log_info "在系统环境中使用 pip 安装 VLLM..." "VLLM"
            echo -e "${INFO} 在系统环境中使用 pip 安装 VLLM..."

            if log_command "VLLM" "Install" "pip install vllm"; then
                log_info "VLLM 安装成功！" "VLLM"
                echo -e "${CHECK} VLLM 安装成功！"
            else
                log_error "VLLM 安装失败，将在首次使用时重试" "VLLM"
                echo -e "${CROSS} VLLM 安装失败，将在首次使用时重试"
            fi
        fi
    fi

    log_info "VLLM 环境准备完成！" "VLLM"
    echo -e "${CHECK} VLLM 环境准备完成！"
    echo ""

    # 显示使用提示
    show_vllm_usage_tips
}

# 显示 VLLM 使用提示
show_vllm_usage_tips() {
    echo -e "${BLUE}🚀 VLLM 使用指南：${NC}"
    echo ""
    echo -e "${BOLD}启动本地 VLLM 服务（推荐）：${NC}"
    echo -e "  ${GREEN}sage llm start${NC}                              # 使用默认模型 (DialoGPT-small)"
    echo -e "  ${GREEN}sage llm start --model <model_name>${NC}        # 使用指定模型"
    echo -e "  ${GREEN}sage llm start --background${NC}                # 后台运行"
    echo -e "  ${GREEN}sage llm status${NC}                            # 查看服务状态"
    echo -e "  ${GREEN}sage llm stop${NC}                              # 停止服务"
    echo ""
    echo -e "${BOLD}推荐模型（按大小排序）：${NC}"
    echo -e "  ${YELLOW}microsoft/DialoGPT-small${NC}       # 轻量模型 (~500MB)  - 适合测试"
    echo -e "  ${YELLOW}microsoft/DialoGPT-medium${NC}      # 中等模型 (~1.5GB) - 适合开发"
    echo -e "  ${YELLOW}microsoft/DialoGPT-large${NC}       # 大模型 (~3GB)     - 更好效果"
    echo -e "  ${YELLOW}meta-llama/Llama-2-7b-chat-hf${NC} # 专业模型 (~14GB)  - 生产环境"
    echo ""
    echo -e "${BOLD}特性：${NC}"
    echo -e "  ${DIM}• 统一的 CLI 命令管理${NC}"
    echo -e "  ${DIM}• 智能参数配置和状态管理${NC}"
    echo -e "  ${DIM}• 支持后台运行和进程监控${NC}"
    echo -e "  ${DIM}• 自动 GPU 内存管理${NC}"
    echo ""
    echo -e "${DIM}更多信息请运行: sage llm --help${NC}"
}

# 验证 VLLM 安装
verify_vllm_installation() {
    echo -e "${GEAR} 检查 VLLM 状态..."

    if command -v vllm >/dev/null 2>&1; then
        local vllm_version=$(vllm --version 2>/dev/null || echo "未知版本")
        echo -e "${CHECK} VLLM 已安装: $vllm_version"
        echo -e "${INFO} 可以运行 sage llm start 启动服务"
        return 0
    else
        echo -e "${INFO} VLLM 尚未安装，建议使用 sage llm start 自动安装并启动服务"
        echo -e "${DIM}提示: sage llm start 将自动安装并启动 VLLM 服务${NC}"
        return 0  # 这不算错误，因为会在首次使用时安装
    fi
}
