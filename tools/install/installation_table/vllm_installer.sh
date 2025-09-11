#!/bin/bash
# SAGE 安装脚本 - VLLM 安装模块
# 简化版本：直接调用现有的 vllm_local_serve.sh 进行安装

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# VLLM 安装函数
install_vllm_packages() {
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    local vllm_script="$project_root/tools/vllm/vllm_local_serve.sh"
    
    echo ""
    echo -e "${GEAR} 准备 VLLM 环境..."
    echo "$(date): 开始准备 VLLM 环境" >> "$log_file"
    
    # 检查 vllm_local_serve.sh 是否存在
    if [[ ! -f "$vllm_script" ]]; then
        echo -e "${CROSS} 未找到 VLLM 启动脚本: $vllm_script"
        echo "错误: 未找到 VLLM 启动脚本" >> "$log_file"
        return 1
    fi
    
    # 给脚本添加执行权限
    chmod +x "$vllm_script"
    
    # 检查是否在 conda 环境中
    if [[ "$CONDA_DEFAULT_ENV" != "" ]] && [[ "$CONDA_DEFAULT_ENV" != "base" ]]; then
        echo -e "${INFO} 检测到 conda 环境: $CONDA_DEFAULT_ENV"
        echo "当前 conda 环境: $CONDA_DEFAULT_ENV" >> "$log_file"
    else
        echo -e "${WARNING} 建议在 conda 环境中使用 VLLM"
        echo "警告: 未检测到 conda 环境" >> "$log_file"
    fi
    
    # 简单检测 vLLM 是否已安装
    if command -v vllm >/dev/null 2>&1; then
        echo -e "${CHECK} VLLM 已安装"
        echo "VLLM 已安装" >> "$log_file"
    else
        echo -e "${INFO} VLLM 未安装，将在首次使用时自动安装"
        echo "VLLM 未安装，将在首次使用时自动安装" >> "$log_file"
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
    echo -e "${BOLD}启动本地 VLLM 服务：${NC}"
    echo -e "  ${GREEN}./tools/vllm/vllm_local_serve.sh${NC}                    # 使用默认模型 (DialoGPT-small)"
    echo -e "  ${GREEN}./tools/vllm/vllm_local_serve.sh <model_name>${NC}       # 使用指定模型"
    echo ""
    echo -e "${BOLD}推荐模型（按大小排序）：${NC}"
    echo -e "  ${YELLOW}microsoft/DialoGPT-small${NC}       # 轻量模型 (~500MB)  - 适合测试"
    echo -e "  ${YELLOW}microsoft/DialoGPT-medium${NC}      # 中等模型 (~1.5GB) - 适合开发"
    echo -e "  ${YELLOW}microsoft/DialoGPT-large${NC}       # 大模型 (~3GB)     - 更好效果"
    echo -e "  ${YELLOW}meta-llama/Llama-2-7b-chat-hf${NC} # 专业模型 (~14GB)  - 生产环境"
    echo ""
    echo -e "${BOLD}特性：${NC}"
    echo -e "  ${DIM}• 自动检测和安装 VLLM（首次使用时）${NC}"
    echo -e "  ${DIM}• 智能网络检测（自动设置 HuggingFace 镜像）${NC}"
    echo -e "  ${DIM}• 模型缓存管理（避免重复下载）${NC}"
    echo -e "  ${DIM}• 友好的用户交互提示${NC}"
    echo ""
    echo -e "${DIM}更多信息请查看: tools/README_vllm_local_serve.md${NC}"
}

# 验证 VLLM 安装
verify_vllm_installation() {
    echo -e "${GEAR} 检查 VLLM 状态..."
    
    if command -v vllm >/dev/null 2>&1; then
        local vllm_version=$(vllm --version 2>/dev/null || echo "未知版本")
        echo -e "${CHECK} VLLM 已安装: $vllm_version"
        return 0
    else
        echo -e "${INFO} VLLM 尚未安装，将在首次使用 vllm_local_serve.sh 时自动安装"
        return 0  # 这不算错误，因为会在首次使用时安装
    fi
}
