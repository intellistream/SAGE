#!/bin/bash
# SAGE 安装脚本 - 核心包安装器 (重构版本)
# 负责通过主sage包统一安装所有依赖

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 导入友好错误处理
if [ -f "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../fixes/friendly_error_handler.sh"
fi

# CI环境检测
if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
elif [ "$SAGE_REMOTE_DEPLOY" = "true" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
else
    export PYTHONNOUSERSITE=1
fi

# 设置pip命令
PIP_CMD="${PIP_CMD:-pip3}"

# 安装核心包 - 新的简化版本
install_core_packages() {
    local install_mode="${1:-dev}"  # 默认为开发模式
    
    # 获取项目根目录并初始化日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/.sage/logs/install.log"
    
    # 确保.sage目录结构存在
    mkdir -p "$project_root/.sage/logs"
    mkdir -p "$project_root/.sage/tmp"
    mkdir -p "$project_root/.sage/cache"
    
    # 初始化日志文件
    echo "SAGE 安装日志 - $(date)" > "$log_file"
    echo "安装模式: $install_mode" >> "$log_file"
    echo "========================================" >> "$log_file"
    
    echo -e "${INFO} 安装 SAGE ($install_mode 模式)..."
    echo -e "${DIM}安装日志: $log_file${NC}"
    echo ""
    
    # 准备安装目标
    local sage_package_path="packages/sage"
    local install_target=""
    
    case "$install_mode" in
        "minimal")
            install_target="$sage_package_path[minimal]"
            echo -e "${GRAY}最小安装：基础功能 + CLI${NC}"
            echo -e "${DIM}包含: sage命令, 基础API, 核心组件${NC}"
            ;;
        "standard") 
            install_target="$sage_package_path[standard]"
            echo -e "${GREEN}标准安装：完整功能 + 科学计算库${NC}"
            echo -e "${DIM}包含: 完整功能 + numpy, pandas, matplotlib, jupyter${NC}"
            ;;
        "dev")
            install_target="$sage_package_path[dev]"
            echo -e "${YELLOW}开发者安装：标准安装 + 开发工具${NC}"
            echo -e "${DIM}包含: 完整功能 + pytest, black, mypy, pre-commit${NC}"
            ;;
        *)
            install_target="$sage_package_path[dev]"
            echo -e "${YELLOW}未知模式，使用开发者模式${NC}"
            ;;
    esac
    
    echo ""
    
    # 检查sage包是否存在
    if [ ! -d "$sage_package_path" ]; then
        echo -e "${CROSS} 错误：找不到SAGE主包目录 ($sage_package_path)"
        echo "$(date): 错误：SAGE主包目录不存在" >> "$log_file"
        return 1
    fi
    
    # 执行安装
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  📦 安装 SAGE ($install_mode 模式)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo -e "${DIM}执行: $PIP_CMD install -e $install_target${NC}"
    echo ""
    
    # 记录安装开始
    echo "$(date): 开始安装 $install_target" >> "$log_file"
    
    # 准备pip安装参数
    local pip_args="--disable-pip-version-check --no-input"
    
    # CI环境额外处理
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        # 检查是否需要 --break-system-packages
        if python3 -c "import sys; exit(0 if '/usr' in sys.prefix else 1)" 2>/dev/null; then
            pip_args="$pip_args --break-system-packages"
            echo -e "${DIM}CI环境: 添加 --break-system-packages${NC}"
        fi
    fi
    
    # 执行安装命令
    if $PIP_CMD install -e "$install_target" $pip_args 2>&1 | tee -a "$log_file"; then
        echo ""
        echo -e "${CHECK} SAGE ($install_mode 模式) 安装成功！"
        echo ""
        
        # 验证sage命令
        echo -e "${DIM}验证 sage 命令...${NC}"
        if command -v sage >/dev/null 2>&1; then
            echo -e "${CHECK} sage 命令已可用"
            echo "$(date): sage 命令验证成功" >> "$log_file"
        else
            echo -e "${WARN} sage 命令不可用，可能需要重启终端"
            echo "$(date): sage 命令验证失败" >> "$log_file"
        fi
        
        echo "$(date): SAGE ($install_mode 模式) 安装成功" >> "$log_file"
        return 0
        
    else
        echo ""
        echo -e "${CROSS} SAGE ($install_mode 模式) 安装失败！"
        echo -e "${DIM}检查日志: $log_file${NC}"
        echo ""
        echo "$(date): SAGE ($install_mode 模式) 安装失败" >> "$log_file"
        return 1
    fi
}

# 安装科学计算包（保持向后兼容）
install_scientific_packages() {
    echo -e "${DIM}科学计算包已包含在标准/开发模式中，跳过单独安装${NC}"
    return 0
}

# 安装开发工具（保持向后兼容）
install_dev_tools() {
    echo -e "${DIM}开发工具已包含在开发模式中，跳过单独安装${NC}"
    return 0
}

# 导出函数
export -f install_core_packages
export -f install_scientific_packages  
export -f install_dev_tools