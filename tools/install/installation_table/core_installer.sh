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
    
    case "$install_mode" in
        "minimal")
            echo -e "${GRAY}最小安装：基础功能 + CLI${NC}"
            echo -e "${DIM}包含: sage命令, 基础API, 核心组件${NC}"
            ;;
        "standard") 
            echo -e "${GREEN}标准安装：完整功能 + 科学计算库${NC}"
            echo -e "${DIM}包含: 完整功能 + numpy, pandas, matplotlib, jupyter${NC}"
            ;;
        "dev")
            echo -e "${YELLOW}开发者安装：标准安装 + 开发工具${NC}"
            echo -e "${DIM}包含: 完整功能 + pytest, black, mypy, pre-commit${NC}"
            ;;
        *)
            echo -e "${YELLOW}未知模式，使用开发者模式${NC}"
            install_mode="dev"
            ;;
    esac
    
    echo ""
    
    # 检查所有必要的包目录是否存在
    local required_packages=("packages/sage-common" "packages/sage-kernel" "packages/sage-tools")
    if [ "$install_mode" != "minimal" ]; then
        required_packages+=("packages/sage-middleware" "packages/sage-libs")
    fi
    # 可选包（存在时添加）
    [ -d "packages/sage-studio" ] && required_packages+=("packages/sage-studio")
    [ -d "packages/sage-apps" ] && required_packages+=("packages/sage-apps")
    [ -d "packages/sage-benchmark" ] && required_packages+=("packages/sage-benchmark")
    required_packages+=("packages/sage")
    
    for package_dir in "${required_packages[@]}"; do
        if [ ! -d "$package_dir" ]; then
            echo -e "${CROSS} 错误：找不到包目录 ($package_dir)"
            echo "$(date): 错误：包目录 $package_dir 不存在" >> "$log_file"
            return 1
        fi
    done
    
    # 执行安装
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  📦 安装 SAGE ($install_mode 模式)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # 准备pip安装参数
    local pip_args="--disable-pip-version-check --no-input"
    
    # CI环境额外处理
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        # 在CI中将包安装到用户site（~/.local），便于跨job缓存与导入
        pip_args="$pip_args --user"
        # 某些系统前缀可能仍需此选项
        if python3 -c "import sys; exit(0 if '/usr' in sys.prefix else 1)" 2>/dev/null; then
            pip_args="$pip_args --break-system-packages"
            echo -e "${DIM}CI环境: 添加 --break-system-packages${NC}"
        fi
        # 确保用户脚本目录在PATH中（供 'sage' 可执行脚本使用）
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${DIM}CI环境: 使用 --user 安装，PATH+=~/.local/bin${NC}"
    fi
    
    echo "$(date): 开始安装本地依赖包" >> "$log_file"
    
    # 本地开发安装策略：
    # 使用 -e (editable) 模式安装，但添加 --no-deps 避免从PyPI下载依赖
    # 因为我们会按正确的依赖顺序手动安装所有包
    local install_flags="-e"
    
    # 第一步：安装基础包（无其他SAGE依赖）
    echo -e "${DIM}步骤 1/3: 安装基础包...${NC}"
    local base_packages=("packages/sage-common" "packages/sage-kernel")
    
    for package_dir in "${base_packages[@]}"; do
        echo -e "${DIM}  正在安装: $package_dir${NC}"
        echo "$(date): 安装 $package_dir" >> "$log_file"
        
        if ! $PIP_CMD install $install_flags "$package_dir" $pip_args --no-deps >> "$log_file" 2>&1; then
            echo -e "${CROSS} 安装 $package_dir 失败！"
            echo "$(date): 安装 $package_dir 失败" >> "$log_file"
            return 1
        fi
    done
    
    # 第二步：安装中间件、应用包和可选组件（对于非minimal模式）
    if [ "$install_mode" != "minimal" ]; then
        echo -e "${DIM}步骤 2/3: 安装中间件和应用包...${NC}"
        local extended_packages=("packages/sage-middleware" "packages/sage-libs")
        # 添加可选包（如果存在）
        [ -d "packages/sage-studio" ] && extended_packages+=("packages/sage-studio")
        [ -d "packages/sage-apps" ] && extended_packages+=("packages/sage-apps")
        [ -d "packages/sage-benchmark" ] && extended_packages+=("packages/sage-benchmark")
        
        for package_dir in "${extended_packages[@]}"; do
            echo -e "${DIM}  正在安装: $package_dir${NC}"
            echo "$(date): 安装 $package_dir" >> "$log_file"
            
            if ! $PIP_CMD install $install_flags "$package_dir" $pip_args --no-deps >> "$log_file" 2>&1; then
                echo -e "${CROSS} 安装 $package_dir 失败！"
                echo "$(date): 安装 $package_dir 失败" >> "$log_file"
                return 1
            fi
        done
        
        # 安装 tools（依赖所有上述包）
        echo -e "${DIM}  正在安装: packages/sage-tools${NC}"
        echo "$(date): 安装 packages/sage-tools" >> "$log_file"
        
        if ! $PIP_CMD install $install_flags "packages/sage-tools" $pip_args --no-deps >> "$log_file" 2>&1; then
            echo -e "${CROSS} 安装 packages/sage-tools 失败！"
            echo "$(date): 安装 packages/sage-tools 失败" >> "$log_file"
            return 1
        fi
    else
        # minimal 模式下，tools 只依赖 common 和 kernel，可以直接安装
        echo -e "${DIM}步骤 2/3: 安装工具包...${NC}"
        echo -e "${DIM}  正在安装: packages/sage-tools${NC}"
        echo "$(date): 安装 packages/sage-tools (minimal mode)" >> "$log_file"
        
        if ! $PIP_CMD install $install_flags "packages/sage-tools" $pip_args --no-deps >> "$log_file" 2>&1; then
            echo -e "${CROSS} 安装 packages/sage-tools 失败！"
            echo "$(date): 安装 packages/sage-tools 失败" >> "$log_file"
            return 1
        fi
    fi
    
    echo -e "${CHECK} 本地依赖包安装完成"
    echo ""
    
    # 第三步：安装主SAGE包（现在所有依赖都已本地可用）
    echo -e "${DIM}步骤 3/3: 安装主SAGE包 (${install_mode}模式)...${NC}"
    echo "$(date): 安装主SAGE包 ($install_mode模式)" >> "$log_file"
    
    # 使用 --no-deps 避免从 PyPI 下载依赖（本地包已安装）
    local install_target="packages/sage[$install_mode]"
    echo -e "${DIM}执行: $PIP_CMD install $install_flags $install_target --no-deps${NC}"
    
    if $PIP_CMD install $install_flags "$install_target" $pip_args --no-deps 2>&1 | tee -a "$log_file"; then
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