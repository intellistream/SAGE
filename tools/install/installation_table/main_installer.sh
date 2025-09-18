#!/bin/bash
# SAGE 安装脚本 - 主安装控制器
# 统一管理不同安装模式的安装流程

# 导入所有安装器
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/interface.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../examination_tools/sage_check.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../download_tools/environment_config.sh"
source "$(dirname "${BASH_SOURCE[0]}")/core_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/scientific_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/dev_installer.sh"
source "$(dirname "${BASH_SOURCE[0]}")/vllm_installer.sh"

# pip 缓存清理函数
clean_pip_cache() {
    local log_file="${1:-install.log}"
    
    echo -e "${BLUE}🧹 清理 pip 缓存...${NC}"
    echo "$(date): 开始清理 pip 缓存" >> "$log_file"
    
    # 检查是否支持 pip cache 命令
    if $PIP_CMD cache --help &>/dev/null; then
        echo -e "${DIM}使用 pip cache purge 清理缓存${NC}"
        
        # 显示缓存大小（如果支持）
        if $PIP_CMD cache info &>/dev/null; then
            local cache_info=$($PIP_CMD cache info 2>/dev/null | grep -E "(Location|Size)" || true)
            if [ -n "$cache_info" ]; then
                echo -e "${DIM}缓存信息:${NC}"
                echo "$cache_info" | sed 's/^/  /'
            fi
        fi
        
        # 执行缓存清理
        if $PIP_CMD cache purge >> "$log_file" 2>&1; then
            echo -e "${CHECK} pip 缓存清理完成"
            echo "$(date): pip 缓存清理成功" >> "$log_file"
        else
            echo -e "${WARNING} pip 缓存清理失败，但继续安装"
            echo "$(date): pip 缓存清理失败" >> "$log_file"
        fi
    else
        echo -e "${DIM}当前 pip 版本不支持 cache 命令，跳过缓存清理${NC}"
        echo "$(date): pip 版本不支持 cache 命令，跳过缓存清理" >> "$log_file"
    fi
    
    echo ""
}

# 主安装函数
install_sage() {
    local mode="${1:-dev}"
    local environment="${2:-conda}"
    local install_vllm="${3:-false}"
    local clean_cache="${4:-true}"
    
    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    
    echo ""
    echo -e "${GEAR} 开始安装 SAGE 包 (${mode} 模式, ${environment} 环境)..."
    if [ "$install_vllm" = "true" ]; then
        echo -e "${PURPLE}包含 VLLM 支持${NC}"
    fi
    echo ""
    
    # 配置安装环境（包含所有检查）
    configure_installation_environment "$environment" "$mode"
    
    # 清理 pip 缓存（如果启用）
    if [ "$clean_cache" = "true" ]; then
        clean_pip_cache "$log_file"
    else
        echo -e "${DIM}跳过 pip 缓存清理（使用 --no-cache-clean 选项）${NC}"
        echo "$(date): 跳过 pip 缓存清理（用户指定）" >> "$log_file"
        echo ""
    fi
    
    # 记录安装开始到日志
    echo "" >> "$log_file"
    echo "========================================" >> "$log_file"
    echo "SAGE 主要安装过程开始 - $(date)" >> "$log_file"
    echo "安装模式: $mode" >> "$log_file"
    echo "安装环境: $environment" >> "$log_file"
    echo "安装 VLLM: $install_vllm" >> "$log_file"
    echo "PIP 命令: $PIP_CMD" >> "$log_file"
    echo "Python 命令: $PYTHON_CMD" >> "$log_file"
    echo "========================================" >> "$log_file"
    
    echo ""
    case "$mode" in
        "minimal")
            echo -e "${BLUE}最小安装模式：仅安装基础 SAGE 包${NC}"
            echo "$(date): 开始最小安装模式" >> "$log_file"
            install_core_packages "$mode"
            ;;
        "standard")
            echo -e "${BLUE}标准安装模式：基础包 + 中间件 + 应用包${NC}"
            echo "$(date): 开始标准安装模式" >> "$log_file"
            install_core_packages "$mode"
            install_scientific_packages
            ;;
        "dev")
            echo -e "${BLUE}开发者安装模式：标准安装 + 开发工具${NC}"
            echo "$(date): 开始开发者安装模式" >> "$log_file"
            install_core_packages "$mode"
            install_scientific_packages
            install_dev_packages
            ;;
        *)
            echo -e "${WARNING} 未知安装模式: $mode，使用开发者模式"
            echo "$(date): 未知安装模式 $mode，使用开发者模式" >> "$log_file"
            install_core_packages "dev"
            install_scientific_packages
            install_dev_packages
            ;;
    esac
    
    echo ""
    echo -e "${CHECK} SAGE 安装完成！"
    
    # 安装 VLLM（如果需要）
    if [ "$install_vllm" = "true" ]; then
        echo ""
        install_vllm_packages
    fi
    
    # 记录安装完成
    echo "$(date): SAGE 安装完成" >> "$log_file"
    if [ "$install_vllm" = "true" ]; then
        echo "$(date): VLLM 安装请求已处理" >> "$log_file"
    fi
    echo "安装结束时间: $(date)" >> "$log_file"
    echo "========================================" >> "$log_file"
    
    # 显示安装信息
    show_install_success "$mode"
}
