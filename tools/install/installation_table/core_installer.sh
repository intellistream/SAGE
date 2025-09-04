#!/bin/bash
# SAGE 安装脚本 - 核心包安装器
# 负责安装 SAGE 核心包（sage-common, sage-kernel, sage-middleware, sage-libs, sage）

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# CI环境检测 - 确保非交互模式
if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
    export PIP_NO_INPUT=1
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    export PYTHONNOUSERSITE=1
fi

# 安装核心包
install_core_packages() {
    local install_mode="${1:-dev}"  # 默认为开发模式，接受参数控制
    
    # 设置环境变量以避免用户站点包干扰
    export PYTHONNOUSERSITE=1
    
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
    local sage_packages=("sage-common" "sage-kernel" "sage-middleware" "sage-libs" "sage")
    
    for package in "${sage_packages[@]}"; do
        local package_path="packages/$package"
        
        if [ -d "$package_path" ]; then
            # 根据安装模式决定安装方式
            if [ "$install_mode" = "dev" ]; then
                echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "${BOLD}  📦 正在安装 $package (开发模式)${NC}"
                echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
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
    if [ "$install_type" = "dev" ]; then
        install_cmd="$pip_cmd install -e $package_path --disable-pip-version-check --no-input"
    else
        install_cmd="$pip_cmd install $package_path --disable-pip-version-check --no-input"
    fi
    
    # 记录安装开始信息到日志
    echo "" >> "$log_file"
    echo "=================================" >> "$log_file"
    echo "$(date): 开始安装 $package_name ($install_type 模式)" >> "$log_file"
    echo "命令: $install_cmd" >> "$log_file"
    echo "=================================" >> "$log_file"
    
    # 使用管道实时显示输出并同时记录到日志
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

# 安装PyPI包并显示实时输出
install_pypi_package_with_output() {
    local pip_cmd="$1"
    local package_name="$2"
    
    # 设置环境变量以避免用户站点包干扰
    export PYTHONNOUSERSITE=1
    
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
    $pip_cmd install "$package_name" --upgrade --disable-pip-version-check 2>&1 | tee -a "$log_file"
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
