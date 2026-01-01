#!/bin/bash

# SAGE 项目 Conda 工具模块
# 提供 Conda 环境管理功能

# 引入日志模块
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/logging.sh"

# 加载配置（如果存在）
if [ -f "$SCRIPT_DIR/../lib/config.sh" ]; then
    source "$SCRIPT_DIR/../lib/config.sh"
fi

# 加载统一的 Conda 安装工具
if [ -f "$SCRIPT_DIR/../lib/conda_install_utils.sh" ]; then
    source "$SCRIPT_DIR/../lib/conda_install_utils.sh"
fi

# 默认配置值
SAGE_CONDA_PATH="${SAGE_CONDA_PATH:-$HOME/miniconda3}"
# 注意：SAGE_ENV_NAME 不在这里设置默认值，应由调用者明确设置
# 只有在确实需要 conda 环境时才设置此变量
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
    print_status "当前 Conda 版本: $(conda --version)"

# 接受 Conda 频道的服务条款
accept_conda_tos() {
    local mode="interactive"
    local forced_choice=""
    local skip_env_test="${SAGE_CONDA_TOS_SKIP_ENV_TEST:-false}"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --auto)
                mode="auto"
                ;;
            --choice)
                forced_choice="$2"
                shift
                ;;
            --choice=*)
                forced_choice="${1#*=}"
                ;;
            --skip-env-test)
                skip_env_test="true"
                ;;
        esac
        shift
    done

    print_header "🔧 Conda 服务条款修复工具"

    # 检查 conda 是否可用
    if ! command -v conda &> /dev/null; then
        print_error "conda 命令不可用"
        print_status "请先确保 Conda 已正确安装并初始化"
        print_status "运行: source ~/.bashrc 或重新打开终端"
        return 1
    fi

    print_status "当前 Conda 版本: $(conda --version)"

    # 显示当前频道配置
    print_header "📋 当前 Conda 配置"
    print_status "当前配置的频道:"
    conda config --show channels 2>/dev/null || echo "  (无自定义频道配置)"

    echo
    print_status "检查服务条款状态..."

    # 检查是否有服务条款问题
    if ! conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
        print_success "✓ 所有服务条款都已接受，无需修复"

        local verify_args=()
        if [ "$skip_env_test" = "true" ]; then
            verify_args+=("--skip-env-test")
        fi
        verify_tos_fix "${verify_args[@]}"
        return 0
    fi

    print_warning "发现未接受的服务条款"

    # 显示需要接受的频道
    echo "需要接受服务条款的频道:"
    local tos_channels=$(conda info 2>&1 | grep -A 10 "Terms of Service have not been accepted" | grep "https://" | sed 's/^[[:space:]]*/  • /' | head -10)
    echo "$tos_channels"

    # 原有主要频道列表
    local main_channels=(
        "https://repo.anaconda.com/pkgs/main"
        "https://repo.anaconda.com/pkgs/r"
    )

    # 获取所有潜在频道：主要 + 从 info 提取的
    local channels=("${main_channels[@]}")
    local additional=$(conda info 2>&1 | grep -oP 'https?://\S+' | sort -u)
    for ch in $additional; do
        if [[ ! " ${channels[*]} " =~ " ${ch} " ]]; then
            channels+=("$ch")
        fi
    done

    local choice=""
    local auto_mode=false
    if [ "$mode" = "auto" ] || [ "${SAGE_CONDA_TOS_AUTO:-false}" = "true" ]; then
        auto_mode=true
        choice="$forced_choice"
        if [[ ! "$choice" =~ ^[1-4]$ ]]; then
            choice="${SAGE_CONDA_TOS_CHOICE:-1}"
        fi
        if [[ ! "$choice" =~ ^[1-4]$ ]]; then
            choice="1"
        fi
        print_status "自动选择方案 $choice"
    else
        echo
        echo "选择解决方案:"
        echo "1) 🏃 快速修复 - 自动接受所有频道的服务条款"
        echo "2) 🔄 使用 conda-forge - 配置使用 conda-forge 频道 (推荐)"
        echo "3) 🛠️  手动修复 - 显示手动修复命令"
        echo "4) ❌ 退出"
        read -p "请输入选择 (1-4): " choice
    fi

    case $choice in
        1)
            print_status "自动接受服务条款..."

            local success_count=0

            for channel in "${channels[@]}"; do
                print_status "接受频道: $channel"
                if conda tos accept --override-channels --channel "$channel" 2>&1; then
                    print_success "✓ 已接受: $channel"
                    ((success_count++))
                else
                    local exit_code=$?
                    if [ $exit_code -eq 1 ]; then
                        print_debug "频道 $channel 的服务条款可能已经接受过"
                    else
                        print_warning "✗ 接受失败 (退出代码: $exit_code): $channel"
                    fi
                fi
            done

            print_debug "处理了 ${#channels[@]} 个频道，成功处理 $success_count 个"
            ;;

        2)
            print_status "配置 conda-forge 频道..."

            conda config --add channels conda-forge
            conda config --set channel_priority strict

            print_success "✓ 已配置 conda-forge 频道为默认"
            print_status "新的频道配置:"
            conda config --show channels
            ;;

        3)
            print_header "🛠️ 手动修复命令"
            echo "请根据频道列表，手动运行以下命令:"
            echo
            for channel in "${channels[@]}"; do
                echo "conda tos accept --override-channels --channel $channel"
            done
            echo
            echo "或者使用 conda-forge:"
            echo "conda config --add channels conda-forge"
            echo "conda config --set channel_priority strict"
            ;;

        4)
            print_status "用户选择退出"
            return 0
            ;;

        *)
            print_error "无效选择"
            return 1
            ;;
    esac

    # 验证修复结果（对于选项3，也运行验证以检查当前状态）
    local verify_args=()
    if [ "$skip_env_test" = "true" ]; then
        verify_args+=("--skip-env-test")
    fi
    verify_tos_fix "${verify_args[@]}"
}

verify_tos_fix() {
    local skip_env_test="false"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-env-test)
                skip_env_test="true"
                ;;
        esac
        shift
    done

    print_header "🧪 验证修复结果"
    print_status "重新检查服务条款状态..."

    if conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
        print_warning "仍有未接受的服务条款，可能需要手动处理"
        print_status "剩余的问题:"
        conda info 2>&1 | grep -A 10 "Terms of Service have not been accepted"
        return 1
    fi

    print_success "✅ 所有服务条款问题已解决！"

    if [ "$skip_env_test" = "true" ]; then
        print_debug "跳过环境创建验证（已指定 --skip-env-test）"
        return 0
    fi

    # 测试创建临时环境
    print_status "测试环境创建功能..."
    local test_env_name="sage_test_$$"

    # 使用统一的 conda_create_bypass 函数
    if declare -f conda_create_bypass >/dev/null 2>&1; then
        if conda_create_bypass "$test_env_name" python=3.11 &>/dev/null; then
            print_success "✓ 环境创建测试通过"
            conda env remove -n "$test_env_name" -y &>/dev/null
            print_debug "已清理测试环境"
            return 0
        fi
    else
        # Fallback: 直接使用清华镜像
        local conda_mirror_main="$TSINGHUA_MIRROR_MAIN"
        if conda create -n "$test_env_name" python=3.11 -y --override-channels -c "$conda_mirror_main" &>/dev/null; then
            print_success "✓ 环境创建测试通过"
            conda env remove -n "$test_env_name" -y &>/dev/null
            print_debug "已清理测试环境"
            return 0
        fi
    fi
    
    print_warning "环境创建测试失败，可能还有其他问题"
    return 1
    fi
}

# 确保 Conda 服务条款已接受（可在非交互模式下使用）
ensure_conda_tos_accepted() {
    local auto_mode=false
    local quiet=false
    local choice="1"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --auto)
                auto_mode=true
                ;;
            --quiet)
                quiet=true
                ;;
            --choice)
                choice="$2"
                shift
                ;;
            --choice=*)
                choice="${1#*=}"
                ;;
        esac
        shift
    done

    if ! command -v conda &> /dev/null; then
        return 0
    fi

    if conda info >/dev/null 2>&1; then
        return 0
    fi

    local conda_info_output
    conda_info_output=$(conda info 2>&1)

    if echo "$conda_info_output" | grep -q "Terms of Service have not been accepted"; then
        if [ "$quiet" != "true" ]; then
            print_warning "检测到 Conda 服务条款未接受，尝试自动修复..."
        fi

        local args=("--skip-env-test")
        if [ "$auto_mode" = true ]; then
            args+=("--auto")
        fi
        if [[ "$choice" =~ ^[1-4]$ ]]; then
            args+=("--choice" "$choice")
        fi

        if accept_conda_tos "${args[@]}"; then
            return 0
        fi

        if [ "$quiet" != "true" ]; then
            print_error "自动接受 Conda 服务条款失败"
        fi
        return 1
    fi

    if [ "$quiet" != "true" ]; then
        print_warning "conda info 执行失败: $conda_info_output"
    fi
    return 1
}

    # 显示当前频道配置
    print_header "📋 当前 Conda 配置"
    print_status "当前配置的频道:"
    conda config --show channels 2>/dev/null || echo "  (无自定义频道配置)"

    echo
    print_status "检查服务条款状态..."

    # 检查是否有服务条款问题
    if ! conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
        print_success "✓ 所有服务条款都已接受，无需修复"
        verify_tos_fix
        return 0
    fi

    print_warning "发现未接受的服务条款"

    # 显示需要接受的频道
    echo "需要接受服务条款的频道:"
    local tos_channels=$(conda info 2>&1 | grep -A 10 "Terms of Service have not been accepted" | grep "https://" | sed 's/^[[:space:]]*/  • /' | head -10)
    echo "$tos_channels"

    # 原有主要频道列表
    local main_channels=(
        "https://repo.anaconda.com/pkgs/main"
        "https://repo.anaconda.com/pkgs/r"
    )

    # 获取所有潜在频道：主要 + 从 info 提取的
    local channels=("${main_channels[@]}")
    local additional=$(conda info 2>&1 | grep -oP 'https?://\S+' | sort -u)
    for ch in $additional; do
        if [[ ! " ${channels[*]} " =~ " ${ch} " ]]; then
            channels+=("$ch")
        fi
    done

    echo
    echo "选择解决方案:"
    echo "1) 🏃 快速修复 - 自动接受所有频道的服务条款"
    echo "2) 🔄 使用 conda-forge - 配置使用 conda-forge 频道 (推荐)"
    echo "3) 🛠️  手动修复 - 显示手动修复命令"
    echo "4) ❌ 退出"

    read -p "请输入选择 (1-4): " choice

    case $choice in
        1)
            print_status "自动接受服务条款..."

            local success_count=0

            for channel in "${channels[@]}"; do
                print_status "接受频道: $channel"
                if conda tos accept --override-channels --channel "$channel" 2>&1; then
                    print_success "✓ 已接受: $channel"
                    ((success_count++))
                else
                    local exit_code=$?
                    if [ $exit_code -eq 1 ]; then
                        print_debug "频道 $channel 的服务条款可能已经接受过"
                    else
                        print_warning "✗ 接受失败 (退出代码: $exit_code): $channel"
                    fi
                fi
            done

            print_debug "处理了 ${#channels[@]} 个频道，成功处理 $success_count 个"
            ;;

        2)
            print_status "配置 conda-forge 频道..."

            conda config --add channels conda-forge
            conda config --set channel_priority strict

            print_success "✓ 已配置 conda-forge 频道为默认"
            print_status "新的频道配置:"
            conda config --show channels
            ;;

        3)
            print_header "🛠️ 手动修复命令"
            echo "请根据频道列表，手动运行以下命令:"
            echo
            for channel in "${channels[@]}"; do
                echo "conda tos accept --override-channels --channel $channel"
            done
            echo
            echo "或者使用 conda-forge:"
            echo "conda config --add channels conda-forge"
            echo "conda config --set channel_priority strict"
            ;;

        4)
            print_status "用户选择退出"
            return 0
            ;;

        *)
            print_error "无效选择"
            return 1
            ;;
    esac

    # 验证修复结果（对于选项3，也运行验证以检查当前状态）
    verify_tos_fix
}

verify_tos_fix() {
    print_header "🧪 验证修复结果"
    print_status "重新检查服务条款状态..."

    if conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
        print_warning "仍有未接受的服务条款，可能需要手动处理"
        print_status "剩余的问题:"
        conda info 2>&1 | grep -A 10 "Terms of Service have not been accepted"
        return 1
    else
        print_success "✅ 所有服务条款问题已解决！"

        # 测试创建临时环境
        print_status "测试环境创建功能..."
        local test_env_name="sage_test_$$"

        # 使用统一的 conda_create_bypass 函数
        if declare -f conda_create_bypass >/dev/null 2>&1; then
            if conda_create_bypass "$test_env_name" python=3.11 &>/dev/null; then
                print_success "✓ 环境创建测试通过"
                conda env remove -n "$test_env_name" -y &>/dev/null
                print_debug "已清理测试环境"
                return 0
            fi
        else
            # Fallback: 直接使用清华镜像
            local conda_mirror_main="$TSINGHUA_MIRROR_MAIN"
            if conda create -n "$test_env_name" python=3.11 -y --override-channels -c "$conda_mirror_main" &>/dev/null; then
                print_success "✓ 环境创建测试通过"
                conda env remove -n "$test_env_name" -y &>/dev/null
                print_debug "已清理测试环境"
                return 0
            fi
        fi
        
        print_warning "环境创建测试失败"
        return 1
    else
            print_warning "环境创建测试失败，可能还有其他问题"
            return 1
        fi
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

    print_status "创建新的 Conda 环境 '$env_name' (Python $python_version)..."

    # 使用清华镜像源绕过 Conda 25.x ToS 限制
    local conda_mirror_main="https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main"
    local conda_mirror_forge="https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge"
    
    # 首先尝试使用清华主频道创建环境
    if conda create -n "$env_name" python="$python_version" -y --override-channels -c "$conda_mirror_main" 2>/dev/null; then
        print_success "使用清华主频道成功创建环境"
        return 0
    fi

    # 如果失败，尝试使用清华 conda-forge 频道
    print_warning "使用主频道失败，尝试使用清华 conda-forge 频道..."
    if conda create -n "$env_name" python="$python_version" -y --override-channels -c "$conda_mirror_forge"; then
        print_success "使用清华 conda-forge 频道成功创建环境"
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

    # 使用清华镜像源绕过 Conda 25.x ToS 限制
    local conda_mirror_main="https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main"
    local conda_mirror_forge="https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge"
    
    # 首先尝试使用清华主频道安装
    if conda install -n "$env_name" -y --override-channels -c "$conda_mirror_main" "${packages[@]}" 2>/dev/null; then
        print_success "使用清华主频道成功安装包"
        return 0
    fi

    # 如果失败，尝试使用清华 conda-forge 频道
    print_warning "使用主频道安装失败，尝试使用 conda-forge 频道..."
    if conda install -n "$env_name" -y --override-channels -c "$conda_mirror_forge" "${packages[@]}"; then
        print_success "使用清华 conda-forge 频道成功安装包"
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

    # 优先接受服务条款，避免后续创建环境时出错
    accept_conda_tos

    # 创建环境
    if ! create_conda_env "$env_name" "$python_version"; then
        return 1
    fi

    # 激活环境 - 更强的重试机制
    local max_retries=3
    local retry_count=0

    while [ $retry_count -lt $max_retries ]; do
        if activate_conda_env "$env_name"; then
            break
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                print_warning "激活失败，重试中... ($retry_count/$max_retries)"
                sleep 2
                # 重新初始化 conda
                init_conda "$conda_path"
            else
                print_error "多次尝试后仍无法激活环境"
                return 1
            fi
        fi
    done

    # 验证环境激活
    if [ "$CONDA_DEFAULT_ENV" != "$env_name" ]; then
        print_warning "环境可能未正确激活，尝试手动设置..."
        export CONDA_DEFAULT_ENV="$env_name"
        export PATH="$conda_path/envs/$env_name/bin:$PATH"
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
