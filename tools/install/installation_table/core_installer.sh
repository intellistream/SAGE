#!/bin/bash
# SAGE 安装脚本 - 核心包安装器
# 负责安装 SAGE 核心包（sage-common, sage-kernel, sage-middleware, sage-libs, sage）

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# CI环境检测 - 确保非交互模式（静默设置，避免重复输出）
if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    # CI环境中不设置PYTHONNOUSERSITE以提高测试速度（静默设置）
elif [ "$SAGE_REMOTE_DEPLOY" = "true" ]; then
    # 远程部署环境设置
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    export PYTHONNOUSERSITE=1  # 远程部署环境需要设置
fi

# 安装核心包
install_core_packages() {
    local install_mode="${1:-dev}"  # 默认为开发模式，接受参数控制
    
    # 只在真正的本地环境中设置PYTHONNOUSERSITE
    if [ "$CI" != "true" ] && [ "$SAGE_REMOTE_DEPLOY" != "true" ] && [ -z "$GITHUB_ACTIONS" ] && [ -z "$GITLAB_CI" ] && [ -z "$JENKINS_URL" ]; then
        export PYTHONNOUSERSITE=1
        echo "# 本地开发环境已设置PYTHONNOUSERSITE=1"
    fi
    
    # 获取项目根目录并初始化日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    
    # 初始化日志文件
    echo "SAGE 安装日志 - $(date)" > "$log_file"
    echo "安装开始时间: $(date)" >> "$log_file"
    echo "安装模式: 核心包安装" >> "$log_file"
    echo "========================================" >> "$log_file"
    
    echo -e "${INFO} 安装核心 SAGE 包..."
    echo -e "${DIM}安装日志将保存到: $log_file${NC}"
    echo ""
    
    # 记录核心包安装开始
    echo "$(date): 开始安装核心 SAGE 包" >> "$log_file"
    
    # SAGE 包安装顺序：sage-common → sage-kernel → sage-middleware → sage-libs → sage
    local sage_packages=("sage-common" "sage-tools" "sage-kernel" "sage-middleware" "sage-libs" "sage")
    
    for package in "${sage_packages[@]}"; do
        local package_path="packages/$package"
        
        if [ -d "$package_path" ]; then
            # 根据安装模式决定安装方式
            if [ "$install_mode" = "dev" ]; then
                echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "${BOLD}  📦 正在安装 $package (开发模式)${NC}"
                echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                
                # 对于 sage-tools，在开发模式下安装完整的 dev 依赖
                if [ "$package" = "sage-tools" ]; then
                    echo -e "${DIM}运行命令: $PIP_CMD install -e $package_path[dev]${NC}"
                    echo -e "${DIM}包含开发工具: black, isort, flake8, pytest, pytest-timeout 等${NC}"
                    echo ""
                    
                    # 使用开发模式安装，包含 [dev] 依赖
                    if install_package_with_output "$PIP_CMD" "$package_path[dev]" "$package" "dev"; then
                        echo ""
                        echo -e "${CHECK} $package [dev] 安装成功！"
                        echo ""
                    else
                        echo ""
                        echo -e "${CROSS} $package [dev] 安装失败！"
                        echo -e "${WARNING} 安装过程中断"
                        echo "$(date): 核心包安装失败，安装中断" >> "$log_file"
                        exit 1
                    fi
                else
                    echo -e "${DIM}运行命令: $PIP_CMD install -e $package_path${NC}"
                    echo ""
                    
                    # 使用开发模式安装
                    if install_package_with_output "$PIP_CMD" "$package_path" "$package" "dev"; then
                        echo ""
                        echo -e "${CHECK} $package 安装成功！"
                        echo ""
                    else
                        echo ""
                        echo -e "${CROSS} $package 安装失败！"
                        echo -e "${WARNING} 安装过程中断"
                        echo "$(date): 核心包安装失败，安装中断" >> "$log_file"
                        exit 1
                    fi
                fi
            else
                echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "${BOLD}  📦 正在安装 $package (生产模式)${NC}"
                echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "${DIM}运行命令: $PIP_CMD install $package_path${NC}"
                echo ""
                
                # 使用生产模式安装
                if install_package_with_output "$PIP_CMD" "$package_path" "$package" "prod"; then
                    echo ""
                    echo -e "${CHECK} $package 安装成功！"
                    echo ""
                else
                    echo ""
                    echo -e "${CROSS} $package 安装失败！"
                    echo -e "${WARNING} 安装过程中断"
                    echo "$(date): 核心包安装失败，安装中断" >> "$log_file"
                    exit 1
                fi
            fi
        else
            echo -e "${WARNING} ⚠️  跳过不存在的包: $package"
            echo "$(date): 跳过不存在的包: $package" >> "$log_file"
            echo ""
        fi
    done
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  🎉 SAGE 核心包安装完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # 记录核心包安装完成
    echo "$(date): 核心 SAGE 包安装完成" >> "$log_file"
    return 0
}

# 安装单个包并显示实时输出
install_package_with_output() {
    local pip_cmd="$1"
    local package_path="$2"
    local package_name="$3"
    local install_type="${4:-dev}"  # dev 或 prod，默认为 dev
    
    # 获取项目根目录
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    
    # 根据安装类型构建命令
    local install_cmd
    local ci_flags=""
    
    # CI环境检测和特殊处理
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        ci_flags="--disable-pip-version-check --no-input"
        echo "🔧 CI环境检测: 使用优化安装选项"
        
        # 检查是否需要 --break-system-packages（对于受管理的Python环境）
        if python3 -c "import sys; print(sys.prefix)" 2>/dev/null | grep -q "^/usr$" || \
           python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))" 2>/dev/null | grep -qE "^/usr/(local/)?lib/python"; then
            ci_flags="$ci_flags --break-system-packages"
            echo "🔧 检测到受管理的Python环境，添加--break-system-packages标志"
        fi
    else
        ci_flags="--disable-pip-version-check --no-input"
    fi
    
    if [ "$install_type" = "dev" ]; then
        install_cmd="$pip_cmd install -e $package_path $ci_flags"
    else
        install_cmd="$pip_cmd install $package_path $ci_flags"
    fi
    
    # 记录安装开始信息到日志
    echo "" >> "$log_file"
    echo "=================================" >> "$log_file"
    echo "$(date): 开始安装 $package_name ($install_type 模式)" >> "$log_file"
    echo "命令: $install_cmd" >> "$log_file"
    echo "工作目录: $(pwd)" >> "$log_file"
    echo "包路径检查: $(ls -la $package_path 2>/dev/null || echo '路径不存在')" >> "$log_file"
    echo "=================================" >> "$log_file"
    
    # 在CI环境中添加超时和调试信息
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        echo "🔍 CI环境调试信息:"
        echo "- Python路径: $(which python3)"
        echo "- Pip版本: $(python3 -m pip --version 2>/dev/null || echo '无法获取pip版本')"
        
        # 预先安装大型依赖以加速后续安装
        if [[ "$package_name" == "sage-kernel" ]]; then
            echo "🚀 CI环境预安装大型依赖..."
            python3 -m pip install --prefer-binary --no-cache-dir torch torchvision numpy || echo "预安装依赖失败，继续主安装"
        fi
        
        # 修复网络检测逻辑 - 增加超时时间并改进错误处理
        local network_status
        network_status=$(python3 -c "
import urllib.request
import socket
try:
    urllib.request.urlopen('https://pypi.org', timeout=10)
    print('✅ 可达')
except (urllib.error.URLError, socket.timeout, socket.error):
    try:
        # 尝试备用地址
        urllib.request.urlopen('https://pypi.python.org', timeout=10)
        print('✅ 可达')
    except:
        print('❌ 不可达')
" 2>/dev/null || echo '❌ 不可达')
        echo "- 网络状态: $network_status"
        
        # CI环境优化：增加超时时间并使用verbose输出
        local ci_pip_cmd="$install_cmd --verbose"
        
        # 为大型包增加更长超时时间（30分钟）
        timeout 1800 $ci_pip_cmd 2>&1 | tee -a "$log_file"
        local install_status=${PIPESTATUS[0]}
        
        # 检查是否超时
        if [ $install_status -eq 124 ]; then
            echo "❌ 安装超时 (30分钟)，可能是网络问题或依赖解析卡住" | tee -a "$log_file"
            echo "💡 建议: 检查网络连接或尝试使用国内镜像源" | tee -a "$log_file"
            
            # 尝试重试一次，使用更保守的参数
            echo "🔄 尝试重新安装（保守模式）..." | tee -a "$log_file"
            timeout 1800 $install_cmd --no-cache-dir --prefer-binary 2>&1 | tee -a "$log_file"
            install_status=${PIPESTATUS[0]}
            
            if [ $install_status -eq 124 ]; then
                echo "❌ 重试仍然超时" | tee -a "$log_file"
                install_status=1
            fi
        fi
    else
        # 普通环境（包括远程部署）：不设置超时
        $install_cmd 2>&1 | tee -a "$log_file"
        local install_status=${PIPESTATUS[0]}
    fi
    
    # 记录安装结果到日志
    if [ $install_status -eq 0 ]; then
        echo "$(date): $package_name 安装成功" >> "$log_file"
    else
        echo "$(date): $package_name 安装失败，退出代码: $install_status" >> "$log_file"
    fi
    echo "=================================" >> "$log_file"
    
    return $install_status
}

# 安装PyPI包并显示实时输出
install_pypi_package_with_output() {
    local pip_cmd="$1"
    local package_name="$2"
    
    # 只在真正的本地环境中设置PYTHONNOUSERSITE
    if [ "$CI" != "true" ] && [ "$SAGE_REMOTE_DEPLOY" != "true" ] && [ -z "$GITHUB_ACTIONS" ] && [ -z "$GITLAB_CI" ] && [ -z "$JENKINS_URL" ]; then
        export PYTHONNOUSERSITE=1
        echo "# 本地开发环境已设置PYTHONNOUSERSITE=1"
    fi
    
    # 获取项目根目录
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    
    # 记录安装开始信息到日志
    echo "" >> "$log_file"
    echo "=================================" >> "$log_file"
    echo "$(date): 开始安装 PyPI 包 $package_name" >> "$log_file"
    echo "命令: $pip_cmd install $package_name --upgrade --disable-pip-version-check" >> "$log_file"
    echo "=================================" >> "$log_file"
    
    # 对于PyPI包，直接执行安装命令并显示输出，同时记录到日志
    # 添加 --upgrade 参数确保安装最新版本
    local install_cmd
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        # CI环境：添加缓存和优化选项
        install_cmd="$pip_cmd install $package_name --upgrade --disable-pip-version-check --progress-bar=on --cache-dir ~/.cache/pip"
    elif [ "$SAGE_REMOTE_DEPLOY" = "true" ]; then
        # 远程部署环境：使用标准选项
        install_cmd="$pip_cmd install $package_name --upgrade --disable-pip-version-check"
    else
        install_cmd="$pip_cmd install $package_name --upgrade --disable-pip-version-check"
    fi
    
    echo "命令: $install_cmd" >> "$log_file"
    $install_cmd 2>&1 | tee -a "$log_file"
    local install_status=${PIPESTATUS[0]}
    
    # 记录安装结果到日志
    if [ $install_status -eq 0 ]; then
        echo "$(date): $package_name 安装成功" >> "$log_file"
    else
        echo "$(date): $package_name 安装失败，退出代码: $install_status" >> "$log_file"
    fi
    echo "=================================" >> "$log_file"
    
    return $install_status
}
