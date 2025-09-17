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

# NVM 自配置函数
self_configure_nvm() {
    local log_file="${1:-install.log}"
    
    echo -e "${DIM}配置 NVM 环境...${NC}"
    echo "$(date): 配置 NVM 环境" >> "$log_file"
    
    # 检查 shell 配置文件
    local shell_rc=""
    if [ -n "$ZSH_VERSION" ]; then
        shell_rc="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        shell_rc="$HOME/.bashrc"
    else
        shell_rc="$HOME/.profile"
    fi
    
    # 添加 nvm 配置到 shell 配置文件
    if [ -f "$shell_rc" ]; then
        # 检查是否已经配置
        if ! grep -q "export NVM_DIR" "$shell_rc"; then
            echo "" >> "$shell_rc"
            echo "# NVM configuration" >> "$shell_rc"
            echo "export NVM_DIR=\"\$HOME/.nvm\"" >> "$shell_rc"
            echo "[ -s \"\$NVM_DIR/nvm.sh\" ] && \. \"\$NVM_DIR/nvm.sh\"" >> "$shell_rc"
            echo "[ -s \"\$NVM_DIR/bash_completion\" ] && \. \"\$NVM_DIR/bash_completion\"" >> "$shell_rc"
            echo "$(date): NVM 配置已添加到 $shell_rc" >> "$log_file"
        fi
    fi
    
    # 立即加载 nvm 到当前会话
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    
    echo -e "${CHECK} NVM 环境配置完成"
    echo "$(date): NVM 环境配置完成" >> "$log_file"
}

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

# 系统依赖安装函数
install_system_dependencies() {
    local log_file="${1:-install.log}"
    
    echo -e "${BLUE}🔧 检查并安装系统依赖...${NC}"
    echo "$(date): 开始检查系统依赖" >> "$log_file"
    
    # 检查操作系统
    if command -v apt &> /dev/null; then
        echo -e "${DIM}检测到 Debian/Ubuntu 系统${NC}"
        
        # 检查 Node.js
        if ! command -v node &> /dev/null; then
            echo -e "${INFO} 安装 Node.js..."
            echo "$(date): 安装 Node.js" >> "$log_file"
            
            # 首先尝试使用 nvm 安装（不需要sudo）
            if [ ! -d "$HOME/.nvm" ]; then
                echo -e "${DIM}安装 NVM...${NC}"
                if curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash; then
                    echo -e "${CHECK} NVM 安装成功"
                    echo "$(date): NVM 安装成功" >> "$log_file"
                else
                    echo -e "${WARNING} NVM 安装失败，尝试系统包管理器"
                    echo "$(date): NVM 安装失败" >> "$log_file"
                fi
            fi
            
            # 加载 nvm 并安装 Node.js
            if [ -d "$HOME/.nvm" ]; then
                echo -e "${DIM}加载 NVM 并安装 Node.js...${NC}"
                export NVM_DIR="$HOME/.nvm"
                [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
                [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
                
                # 安装 Node.js 18
                if nvm install 18 && nvm use 18 && nvm alias default 18; then
                    echo -e "${CHECK} Node.js 18 安装成功 (使用nvm)"
                    echo "$(date): Node.js 18 安装成功 (nvm)" >> "$log_file"
                    
                    # 验证安装
                    local node_version=$(node --version 2>/dev/null)
                    local npm_version=$(npm --version 2>/dev/null)
                    echo -e "${CHECK} Node.js 版本: $node_version"
                    echo -e "${CHECK} npm 版本: $npm_version"
                    
                    # 将 nvm 配置添加到 shell 配置文件
                    self_configure_nvm "$log_file"
                else
                    echo -e "${WARNING} NVM Node.js 安装失败，尝试系统包管理器"
                    echo "$(date): NVM Node.js 安装失败" >> "$log_file"
                fi
            fi
            
            # 如果 nvm 安装失败，尝试系统包管理器
            if ! command -v node &> /dev/null; then
                echo -e "${DIM}尝试系统包管理器安装 Node.js...${NC}"
                if apt update && apt install -y nodejs npm; then
                    echo -e "${CHECK} Node.js 安装成功 (apt)"
                    echo "$(date): Node.js 安装成功 (apt)" >> "$log_file"
                elif sudo apt update && sudo apt install -y nodejs npm; then
                    echo -e "${CHECK} Node.js 安装成功 (apt, sudo)"
                    echo "$(date): Node.js 安装成功 (apt, sudo)" >> "$log_file"
                else
                    echo -e "${WARNING} Node.js 安装失败，但继续安装过程"
                    echo "$(date): Node.js 安装失败" >> "$log_file"
                fi
            fi
        else
            local node_version=$(node --version 2>/dev/null)
            echo -e "${CHECK} Node.js 已安装: $node_version"
            echo "$(date): Node.js 已安装 ($node_version)" >> "$log_file"
        fi
        
    elif command -v yum &> /dev/null; then
        echo -e "${DIM}检测到 RHEL/CentOS 系统${NC}"
        
        # 检查 Node.js
        if ! command -v node &> /dev/null; then
            echo -e "${INFO} 安装 Node.js..."
            echo "$(date): 安装 Node.js (yum)" >> "$log_file"
            
            # 首先尝试使用 nvm 安装（不需要sudo）
            if [ ! -d "$HOME/.nvm" ]; then
                echo -e "${DIM}安装 NVM...${NC}"
                if curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash; then
                    echo -e "${CHECK} NVM 安装成功"
                    echo "$(date): NVM 安装成功 (yum)" >> "$log_file"
                else
                    echo -e "${WARNING} NVM 安装失败，尝试系统包管理器"
                    echo "$(date): NVM 安装失败 (yum)" >> "$log_file"
                fi
            fi
            
            # 加载 nvm 并安装 Node.js
            if [ -d "$HOME/.nvm" ]; then
                echo -e "${DIM}加载 NVM 并安装 Node.js...${NC}"
                export NVM_DIR="$HOME/.nvm"
                [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
                [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
                
                # 安装 Node.js 18
                if nvm install 18 && nvm use 18 && nvm alias default 18; then
                    echo -e "${CHECK} Node.js 18 安装成功 (使用nvm)"
                    echo "$(date): Node.js 18 安装成功 (nvm, yum)" >> "$log_file"
                    
                    # 将 nvm 配置添加到 shell 配置文件
                    self_configure_nvm "$log_file"
                else
                    echo -e "${WARNING} NVM Node.js 安装失败，尝试系统包管理器"
                    echo "$(date): NVM Node.js 安装失败 (yum)" >> "$log_file"
                fi
            fi
            
            # 如果 nvm 安装失败，尝试系统包管理器
            if ! command -v node &> /dev/null; then
                echo -e "${DIM}尝试系统包管理器安装 Node.js...${NC}"
                if yum install -y nodejs npm; then
                    echo -e "${CHECK} Node.js 安装成功 (yum)"
                    echo "$(date): Node.js 安装成功 (yum)" >> "$log_file"
                elif sudo yum install -y nodejs npm; then
                    echo -e "${CHECK} Node.js 安装成功 (yum, sudo)"
                    echo "$(date): Node.js 安装成功 (yum, sudo)" >> "$log_file"
                else
                    echo -e "${WARNING} Node.js 安装失败，但继续安装过程"
                    echo "$(date): Node.js 安装失败 (yum)" >> "$log_file"
                fi
            fi
        else
            local node_version=$(node --version 2>/dev/null)
            echo -e "${CHECK} Node.js 已安装: $node_version"
            echo "$(date): Node.js 已安装 ($node_version)" >> "$log_file"
        fi
        
    else
        echo -e "${WARNING} 未检测到支持的包管理器 (apt/yum)"
        echo -e "${DIM}请手动安装 Node.js 18+ 以使用 Studio 功能${NC}"
        echo "$(date): 未检测到包管理器，跳过系统依赖安装" >> "$log_file"
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
    
    # 安装系统依赖
    install_system_dependencies "$log_file"
    
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
            echo -e "${BLUE}最小安装模式：仅安装核心 SAGE 包${NC}"
            echo "$(date): 开始最小安装模式" >> "$log_file"
            install_core_packages "$mode"
            ;;
        "standard")
            echo -e "${BLUE}标准安装模式：核心包 + 科学计算库${NC}"
            echo -e "${DIM}包含: numpy, pandas, matplotlib, scipy, jupyter${NC}"
            echo "$(date): 开始标准安装模式" >> "$log_file"
            install_core_packages "$mode"
            install_scientific_packages
            ;;
        "dev")
            echo -e "${BLUE}开发者安装模式：标准包 + 开发工具${NC}"
            echo -e "${DIM}包含: 标准安装 + pytest, black, mypy, pre-commit${NC}"
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
