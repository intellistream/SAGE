#!/bin/bash
# SAGE 安装脚本 - VLLM 安装模块
# 简化版本：直接调用现有的 vllm_local_serve.sh 进行安装

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# VLLM 安装函数
install_vllm_packages() {
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"

    echo ""
    echo -e "${GEAR} 准备 VLLM 环境..."
    mkdir -p "$(dirname "$log_file")"
    echo "$(date): 开始准备 VLLM 环境" >> "$log_file"

    # 检查是否在 conda 环境中
    if [[ "$CONDA_DEFAULT_ENV" != "" ]] && [[ "$CONDA_DEFAULT_ENV" != "base" ]]; then
        echo -e "${INFO} 检测到 conda 环境: $CONDA_DEFAULT_ENV"
        echo "当前 conda 环境: $CONDA_DEFAULT_ENV" >> "$log_file"
    else
        echo -e "${WARNING} 建议在 conda 环境中使用 VLLM"
        echo "警告: 未检测到 conda 环境" >> "$log_file"
    fi

    # 检测并安装 vLLM
    if command -v vllm >/dev/null 2>&1; then
        echo -e "${CHECK} VLLM 已安装"
        echo "VLLM 已安装" >> "$log_file"
    else
        echo -e "${INFO} 正在安装 VLLM..."
        echo "$(date): 开始安装 VLLM" >> "$log_file"

        # 直接使用 pip 安装 VLLM，因为：
        # 1. conda-forge 的版本通常较旧（0.9.2 vs 最新的 0.10.1.1）
        # 2. pip 版本更新更及时
        # 3. 避免复杂的依赖冲突

        if [[ "$CONDA_DEFAULT_ENV" != "" ]] && [[ "$CONDA_DEFAULT_ENV" != "base" ]]; then
            echo -e "${INFO} 在 conda 环境 '$CONDA_DEFAULT_ENV' 中使用 pip 安装 VLLM..."
            echo "$(date): 在 conda 环境中使用 pip 安装" >> "$log_file"

            if conda run -n "$CONDA_DEFAULT_ENV" pip install vllm >> "$log_file" 2>&1; then
                echo -e "${CHECK} VLLM 安装成功！"
                echo "$(date): VLLM 安装成功" >> "$log_file"
            else
                echo -e "${CROSS} VLLM 安装失败，将在首次使用时重试"
                echo "$(date): VLLM 安装失败，将延迟安装" >> "$log_file"
            fi
        else
            echo -e "${INFO} 在系统环境中使用 pip 安装 VLLM..."
            echo "$(date): 在系统环境中使用 pip 安装" >> "$log_file"

            if pip install vllm >> "$log_file" 2>&1; then
                echo -e "${CHECK} VLLM 安装成功！"
                echo "$(date): VLLM 安装成功" >> "$log_file"
            else
                echo -e "${CROSS} VLLM 安装失败，将在首次使用时重试"
                echo "$(date): VLLM 安装失败，将延迟安装" >> "$log_file"
            fi
        fi
    fi

    echo -e "${CHECK} VLLM 环境准备完成！"
    echo ""

    # 显示使用提示
    show_vllm_usage_tips

    echo "$(date): VLLM 环境准备完成" >> "$log_file"
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
