#!/bin/bash

# SAGE 项目 Conda 工具模块
# 提供 Conda 环境管理功能

# 引入日志模块
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/logging.sh"

# 加载配置（如果存在）
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    source "$SCRIPT_DIR/config.sh"
fi

# 默认配置值
SAGE_CONDA_PATH="${SAGE_CONDA_PATH:-$HOME/miniconda3}"
SAGE_ENV_NAME="${SAGE_ENV_NAME:-sage}"
SAGE_PYTHON_VERSION="${SAGE_PYTHON_VERSION:-3.11}"

# 检查命令是否存在（可选）
check_command_optional() {
    if ! command -v $1 &> /dev/null; then
        return 1
    fi
    return 0
}

# 获取系统信息
get_system_info() {
    local arch=$(uname -m)
    local os=$(uname -s)
    
    echo "$os:$arch"
}

# 获取 Miniconda 下载 URL
get_miniconda_url() {
    local system_info=$(get_system_info)
    local os=$(echo "$system_info" | cut -d':' -f1)
    local arch=$(echo "$system_info" | cut -d':' -f2)
    
    if [ "$os" = "Linux" ]; then
        if [ "$arch" = "x86_64" ]; then
            echo "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        elif [ "$arch" = "aarch64" ]; then
            echo "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"
        else
            print_error "不支持的架构: $arch"
            return 1
        fi
    elif [ "$os" = "Darwin" ]; then
        if [ "$arch" = "x86_64" ]; then
            echo "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        elif [ "$arch" = "arm64" ]; then
            echo "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
        else
            print_error "不支持的架构: $arch"
            return 1
        fi
    else
        print_error "不支持的操作系统: $os"
        return 1
    fi
}

# 检查 Conda 是否已安装
is_conda_installed() {
    check_command_optional conda
}

# 下载文件（支持 wget 和 curl）
download_file() {
    local url="$1"
    local output="$2"
    
    if check_command_optional wget; then
        wget -O "$output" "$url"
    elif check_command_optional curl; then
        curl -L -o "$output" "$url"
    else
        print_error "需要 wget 或 curl 来下载文件"
        return 1
    fi
}

# 安装 Miniconda
install_miniconda() {
    local install_path="${1:-$SAGE_CONDA_PATH}"
    
    print_header "🐍 安装 Miniconda"
    
    # 检查是否已安装 conda
    if is_conda_installed; then
        print_success "Conda 已安装，跳过 Miniconda 安装"
        return 0
    fi
    
    # 获取下载 URL
    local miniconda_url
    if ! miniconda_url=$(get_miniconda_url); then
        return 1
    fi
    
    print_status "下载 Miniconda 安装包..."
    local temp_dir=$(mktemp -d)
    local installer="$temp_dir/miniconda.sh"
    
    if ! download_file "$miniconda_url" "$installer"; then
        print_error "下载 Miniconda 失败"
        rm -rf "$temp_dir"
        return 1
    fi
    
    print_status "安装 Miniconda 到 $install_path..."
    if ! bash "$installer" -b -p "$install_path"; then
        print_error "Miniconda 安装失败"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # 清理安装包
    rm -rf "$temp_dir"
    
    # 初始化 conda
    print_status "初始化 Conda..."
    "$install_path/bin/conda" init bash
    
    # 添加到当前会话的 PATH
    export PATH="$install_path/bin:$PATH"
    
    print_success "Miniconda 安装完成"
    print_warning "请重新打开终端或运行 'source ~/.bashrc' 以使 conda 命令生效"
    
    return 0
}

# 初始化 Conda 环境
init_conda() {
    local conda_path="${1:-$SAGE_CONDA_PATH}"
    
    # 首先尝试从 bashrc 加载 conda 初始化
    if [ -f "$HOME/.bashrc" ]; then
        # 检查 bashrc 中是否有 conda 初始化代码
        if grep -q "# >>> conda initialize >>>" "$HOME/.bashrc"; then
            print_status "从 ~/.bashrc 加载 conda 初始化..."
            # 提取并执行 conda 初始化部分
            eval "$(sed -n '/# >>> conda initialize >>>/,/# <<< conda initialize <<</p' "$HOME/.bashrc")"
        fi
    fi
    
    if ! is_conda_installed; then
        # 尝试从指定路径加载 conda
        if [ -f "$conda_path/bin/conda" ]; then
            export PATH="$conda_path/bin:$PATH"
            if [ -f "$conda_path/etc/profile.d/conda.sh" ]; then
                print_status "从 conda 安装路径加载初始化脚本..."
                source "$conda_path/etc/profile.d/conda.sh"
            fi
        else
            print_error "Conda 未找到，请确保 Miniconda 已正确安装"
            return 1
        fi
    fi
    
    # 验证 conda 是否可用
    if ! command -v conda &> /dev/null; then
        print_error "Conda 初始化失败，请手动运行 'conda init bash' 然后重新启动终端"
        return 1
    fi
    
    return 0
}

# 检查 Conda 环境是否存在
conda_env_exists() {
    local env_name="$1"
    conda env list | grep -q "^$env_name "
}

# 接受 Conda 频道的服务条款
accept_conda_tos() {
    print_status "检查并接受 Conda 服务条款..."
    
    # 检查是否需要接受服务条款
    if conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
        print_status "需要接受 Conda 服务条款..."
        
        # 静默接受主要频道的服务条款
        local main_channels=(
            "https://repo.anaconda.com/pkgs/main"
            "https://repo.anaconda.com/pkgs/r"
        )
        
        for channel in "${main_channels[@]}"; do
            print_debug "接受频道 '$channel' 的服务条款..."
            if conda tos accept --override-channels --channel "$channel" 2>/dev/null; then
                print_debug "成功接受频道 '$channel' 的服务条款"
            else
                print_debug "频道 '$channel' 的服务条款可能已经接受或不需要"
            fi
        done
        
        # 验证是否成功
        if conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
            print_warning "部分服务条款可能仍需手动接受"
            print_warning "如果遇到问题，可以手动运行: conda tos accept --override-channels --channel <频道名>"
        else
            print_success "Conda 服务条款接受完成"
        fi
    else
        print_debug "Conda 服务条款已经接受，无需重复操作"
    fi
}

# 创建 Conda 环境
create_conda_env() {
    local env_name="$1"
    local python_version="${2:-3.11}"
    
    if conda_env_exists "$env_name"; then
        print_status "Conda 环境 '$env_name' 已存在，跳过创建步骤..."
        return 0
    fi
    
    # 接受 Conda 频道的服务条款
    accept_conda_tos
    
    print_status "创建新的 Conda 环境 '$env_name' (Python $python_version)..."
    
    # 首先尝试使用默认频道创建环境
    if conda create -n "$env_name" python="$python_version" -y 2>/dev/null; then
        print_success "使用默认频道成功创建环境"
        return 0
    fi
    
    # 如果失败，尝试使用 conda-forge 频道
    print_warning "使用默认频道失败，尝试使用 conda-forge 频道..."
    if conda create -n "$env_name" -c conda-forge python="$python_version" -y; then
        print_success "使用 conda-forge 频道成功创建环境"
        return 0
    else
        print_error "环境创建失败"
        return 1
    fi
}

# 激活 Conda 环境
activate_conda_env() {
    local env_name="$1"
    
    print_status "激活 Conda 环境 '$env_name'..."
    
    # 确保 conda 命令可用
    if ! command -v conda &> /dev/null; then
        print_error "conda 命令不可用，请先运行 init_conda"
        return 1
    fi
    
    # 检查环境是否存在
    if ! conda_env_exists "$env_name"; then
        print_error "Conda 环境 '$env_name' 不存在"
        print_status "可用的环境列表:"
        conda env list
        return 1
    fi
    
    # 尝试激活环境
    if conda activate "$env_name" 2>/dev/null; then
        print_success "成功激活环境 '$env_name'"
        return 0
    else
        print_error "无法激活 Conda 环境 '$env_name'"
        print_warning "请尝试以下解决方案:"
        print_warning "1. 运行 'conda init bash' 然后重新启动终端"
        print_warning "2. 或者运行 'source ~/.bashrc'"
        print_warning "3. 然后重新运行此脚本"
        return 1
    fi
}

# 在指定环境中安装包
install_conda_packages() {
    local env_name="$1"
    shift
    local packages=("$@")
    
    if [ ${#packages[@]} -eq 0 ]; then
        print_warning "没有指定要安装的包"
        return 0
    fi
    
    print_status "在环境 '$env_name' 中安装包: ${packages[*]}"
    
    # 首先尝试使用默认频道安装
    if conda install -n "$env_name" "${packages[@]}" -y 2>/dev/null; then
        print_success "使用默认频道成功安装包"
        return 0
    fi
    
    # 如果失败，尝试使用 conda-forge 频道
    print_warning "使用默认频道安装失败，尝试使用 conda-forge 频道..."
    if conda install -n "$env_name" -c conda-forge "${packages[@]}" -y; then
        print_success "使用 conda-forge 频道成功安装包"
        return 0
    else
        print_error "包安装失败: ${packages[*]}"
        return 1
    fi
}

# 设置完整的 SAGE 开发环境
setup_sage_environment() {
    local env_name="${1:-$SAGE_ENV_NAME}"
    local python_version="${2:-$SAGE_PYTHON_VERSION}"
    local conda_path="${3:-$SAGE_CONDA_PATH}"
    
    print_header "🛠️ 创建 SAGE 开发环境"
    
    # 初始化 conda
    if ! init_conda "$conda_path"; then
        return 1
    fi
    
    # 创建环境
    if ! create_conda_env "$env_name" "$python_version"; then
        return 1
    fi
    
    # 激活环境
    if ! activate_conda_env "$env_name"; then
        return 1
    fi
    
    # 安装基础开发工具
    print_status "安装基础开发工具..."
    install_conda_packages "$env_name" pip setuptools wheel build
    
    # 安装常用科学计算包
    print_status "安装科学计算依赖..."
    install_conda_packages "$env_name" numpy pandas matplotlib jupyter notebook
    
    print_success "SAGE 环境设置完成"
    
    return 0
}

# 获取当前激活的 Conda 环境
get_current_conda_env() {
    if [ -n "$CONDA_DEFAULT_ENV" ]; then
        echo "$CONDA_DEFAULT_ENV"
    else
        echo "base"
    fi
}

# 显示 Conda 环境信息
show_conda_env_info() {
    local env_name="${1:-$(get_current_conda_env)}"
    
    print_header "🌐 Conda 环境信息"
    
    echo "当前环境: $env_name"
    echo "Python 版本: $(python --version 2>/dev/null || echo '未知')"
    echo "Conda 版本: $(conda --version 2>/dev/null || echo '未知')"
    
    if conda env list | grep -q "^$env_name "; then
        echo "环境路径: $(conda env list | grep "^$env_name " | awk '{print $2}')"
    fi
}
