#!/bin/bash
# SAGE 安装脚本 - Conda 环境管理工具
# 处理 conda 环境的创建、激活、管理等操作

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# CI环境或远程部署检测 - 确保非交互模式
if [ "$CI" = "true" ] || [ "$SAGE_REMOTE_DEPLOY" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
    export CONDA_ALWAYS_YES=true  # conda的非交互模式
    # 只在CI环境中注释掉PYTHONNOUSERSITE以提高测试速度，远程部署仍需要设置
    if [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        # export PYTHONNOUSERSITE=1  # CI环境中注释掉以提高runner测试速度
        echo "# CI环境中跳过PYTHONNOUSERSITE设置"
    else
        export PYTHONNOUSERSITE=1  # 远程部署环境仍需要设置
    fi
fi

# 询问用户是否创建新的 conda 环境
ask_conda_environment() {
    if ! command -v conda &> /dev/null; then
        return 1  # conda 不可用，跳过
    fi
    
    # 如果已经指定了环境名，直接使用
    if [ -n "$SAGE_ENV_NAME" ]; then
        echo ""
        echo -e "${GEAR} ${BOLD}Conda 环境设置${NC}"
        echo ""
        echo -e "${INFO} 使用指定的环境名: ${GREEN}$SAGE_ENV_NAME${NC}"
        create_conda_environment "$SAGE_ENV_NAME"
        return $?
    fi
    
    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    
    echo ""
    echo -e "${GEAR} ${BOLD}Conda 环境设置${NC}"
    echo ""
    echo -e "${BLUE}检测到 Conda 已安装，建议为 SAGE 创建独立环境${NC}"
    echo ""
    echo -e "选项："
    echo -e "  ${GREEN}[1] 创建新的 SAGE 环境 (环境名：sage) ${BOLD}[推荐]${NC}"
    echo -e "  [2] 使用当前环境"
    echo -e "  [3] 手动指定环境名"
    echo ""
    echo -e "${DIM}注意: 如果选择创建新环境但失败，将自动回退到当前环境${NC}"
    echo ""
    
    # 记录到日志
    echo "$(date): 用户选择 Conda 环境配置" >> "$log_file"
    
    # 如果是CI环境或远程部署，自动选择选项1
    if [ "$CI" = "true" ] || [ "$SAGE_REMOTE_DEPLOY" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        echo -e "${INFO} 检测到CI/远程部署环境，自动选择选项1：创建新的 SAGE 环境"
        echo "$(date): CI/远程部署环境自动选择选项1" >> "$log_file"
        conda_choice=1
    else
        # 交互模式，询问用户选择
        while true; do
            echo -ne "${BLUE}请选择 [1-3]: ${NC}"
            read -r conda_choice
            echo "$(date): 用户选择: $conda_choice" >> "$log_file"
            
            case $conda_choice in
                1|2|3)
                    break
                    ;;
                *)
                    echo -e "${WARNING} 无效选择，请输入 1-3"
                    ;;
            esac
        done
    fi
    
    # 处理用户选择
    case $conda_choice in
        1)
            SAGE_ENV_NAME="sage"
            export SAGE_ENV_NAME  # 导出环境变量
            create_conda_environment "$SAGE_ENV_NAME"
            ;;
        2)
            echo -e "${INFO} 将在当前环境中安装 SAGE"
            echo "$(date): 用户选择使用当前环境" >> "$log_file"
            SAGE_ENV_NAME=""
            export SAGE_ENV_NAME
            ;;
        3)
            if [ "$CI" = "true" ] || [ "$SAGE_REMOTE_DEPLOY" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
                # CI/远程部署环境不应该到达这里，但万一到了就默认使用sage
                echo -e "${WARNING} CI/远程部署环境中不应选择选项3，回退到选项1"
                SAGE_ENV_NAME="sage"
                export SAGE_ENV_NAME
                create_conda_environment "$SAGE_ENV_NAME"
            else
                echo -ne "${BLUE}请输入环境名称: ${NC}"
                read -r custom_env_name
                echo "$(date): 用户输入自定义环境名: $custom_env_name" >> "$log_file"
                if [[ -n "$custom_env_name" ]]; then
                    SAGE_ENV_NAME="$custom_env_name"
                    export SAGE_ENV_NAME  # 导出环境变量
                    create_conda_environment "$SAGE_ENV_NAME"
                else
                    echo -e "${WARNING} 环境名不能为空，使用默认名称: sage"
                    SAGE_ENV_NAME="sage"
                    export SAGE_ENV_NAME
                    create_conda_environment "$SAGE_ENV_NAME"
                fi
            fi
            ;;
        *)
            echo -e "${WARNING} 无效选择，使用默认选项1"
            SAGE_ENV_NAME="sage"
            export SAGE_ENV_NAME
            create_conda_environment "$SAGE_ENV_NAME"
            ;;
    esac
}

# 创建 conda 环境
create_conda_environment() {
    local env_name="$1"
    
    # 获取项目根目录和日志文件
    local project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    local log_file="$project_root/install.log"
    
    echo -e "${INFO} 创建 Conda 环境: $env_name"
    echo "$(date): 开始创建 Conda 环境: $env_name" >> "$log_file"
    
    # 检查环境是否已存在
    if conda env list | grep -q "^$env_name "; then
        echo -e "${WARNING} 环境 '$env_name' 已存在"
        echo "$(date): 环境 '$env_name' 已存在" >> "$log_file"
        
        # 如果是CI环境或远程部署，自动选择重新创建
        if [ "$CI" = "true" ] || [ "$SAGE_REMOTE_DEPLOY" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
            echo -e "${INFO} CI/远程部署环境检测到，自动删除并重新创建环境"
            echo "$(date): CI/远程部署环境自动选择重新创建环境" >> "$log_file"
            recreate="y"
        else
            echo -ne "${BLUE}是否删除并重新创建? [y/N]: ${NC}"
            read -r recreate
            echo "$(date): 用户选择重新创建: $recreate" >> "$log_file"
        fi
        
        case "$recreate" in
            [yY]|[yY][eE][sS])
                echo -e "${INFO} 删除现有环境..."
                echo -e "${DIM}执行命令: conda env remove -n $env_name -y${NC}"
                echo "$(date): 删除现有环境 $env_name" >> "$log_file"
                local remove_output=$(conda env remove -n "$env_name" -y 2>&1 | tee -a "$log_file")
                if [ $? -eq 0 ]; then
                    echo -e "${CHECK} 环境删除成功"
                    echo "$(date): 环境删除成功" >> "$log_file"
                else
                    echo -e "${WARNING} 环境删除出现问题: $remove_output"
                    echo -e "${INFO} 继续尝试创建..."
                    echo "$(date): 环境删除出现问题，继续创建" >> "$log_file"
                fi
                ;;
            *)
                echo -e "${INFO} 将在现有环境中安装"
                echo "$(date): 用户选择使用现有环境" >> "$log_file"
                activate_conda_environment "$env_name"
                return 0
                ;;
        esac
    fi
    
    # 创建环境
    echo -e "${INFO} 创建新环境 '$env_name' (Python 3.11)..."
    
    # 在CI环境中使用更快的创建方式
    if [ "$CI" = "true" ] || [ "$SAGE_REMOTE_DEPLOY" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
        if command -v mamba >/dev/null 2>&1; then
            echo -e "${DIM}执行命令: mamba create -n $env_name python=3.11 -y${NC}"
            local create_cmd="mamba create -n $env_name python=3.11 -y"
        else
            echo -e "${DIM}执行命令: conda create -n $env_name python=3.11 -y --solver=libmamba${NC}"
            local create_cmd="conda create -n $env_name python=3.11 -y --solver=libmamba"
        fi
    else
        echo -e "${DIM}执行命令: conda create -n $env_name python=3.11 -y${NC}"
        local create_cmd="conda create -n $env_name python=3.11 -y"
    fi
    
    # 先检查conda是否正常工作
    if ! conda info &>/dev/null; then
        echo -e "${CROSS} Conda 无法正常工作，请检查 conda 安装"
        echo -e "${DIM}尝试运行: conda info${NC}"
        SAGE_ENV_NAME=""
        return 1
    fi
    
    # 创建环境并显示详细输出
    local create_output=$($create_cmd 2>&1)
    local create_status=$?
    
    # 验证环境是否真正创建成功
    local env_created=false
    if [ $create_status -eq 0 ]; then
        # 等待一下让conda完成操作
        sleep 2
        # 检查环境是否真的存在
        if conda env list | grep -q "^$env_name "; then
            env_created=true
            echo -e "${CHECK} 环境创建成功并验证"
        else
            echo -e "${CROSS} 环境创建命令成功但环境不存在，可能是权限或磁盘空间问题"
            env_created=false
        fi
    fi
    
    if [ "$env_created" = true ]; then
        activate_conda_environment "$env_name"
    else
        echo -e "${CROSS} 环境创建失败，详细错误信息："
        echo -e "${DIM}$create_output${NC}"
        echo ""
        echo -e "${INFO} 尝试诊断问题..."
        
        # 检查磁盘空间
        local available_space=$(df -h ~/.conda 2>/dev/null | awk 'NR==2{print $4}' || echo "未知")
        echo -e "${INFO} ~/.conda 目录可用空间: $available_space"
        
        # 检查权限
        if [ ! -w ~/.conda/envs 2>/dev/null ]; then
            echo -e "${WARNING} ~/.conda/envs 目录权限问题"
            echo -e "${DIM}尝试: mkdir -p ~/.conda/envs && chmod 755 ~/.conda/envs${NC}"
        fi
        
        # 检查常见问题
        if echo "$create_output" | grep -q "PackagesNotFoundError"; then
            echo -e "${WARNING} Python 3.11 包未找到，尝试使用 Python 3.10"
            echo -e "${DIM}执行命令: conda create -n $env_name python=3.10 -y${NC}"
            local fallback_output=$(conda create -n "$env_name" python=3.10 -y 2>&1)
            local fallback_status=$?
            if [ $fallback_status -eq 0 ]; then
                sleep 2
                if conda env list | grep -q "^$env_name "; then
                    echo -e "${CHECK} 环境创建成功 (使用 Python 3.10)"
                    activate_conda_environment "$env_name"
                    return 0
                fi
            fi
            echo -e "${CROSS} Python 3.10 也失败了：$fallback_output"
        elif echo "$create_output" | grep -q "CondaHTTPError\|CondaSSLError"; then
            echo -e "${WARNING} 网络连接问题，请检查网络设置或使用国内镜像源"
            echo -e "${DIM}建议: conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/${NC}"
        elif echo "$create_output" | grep -q "DiskSpaceError\|No space left"; then
            echo -e "${WARNING} 磁盘空间不足，请清理磁盘后重试"
        elif echo "$create_output" | grep -q "PermissionError"; then
            echo -e "${WARNING} 权限错误，可能需要修复conda目录权限"
            echo -e "${DIM}尝试: sudo chown -R $(whoami) ~/.conda${NC}"
        else
            echo -e "${WARNING} 未知错误，建议手动检查 conda 配置"
            echo -e "${DIM}尝试手动创建: conda create -n $env_name python=3.11 -y${NC}"
        fi
        
        echo -e "${INFO} 将使用当前环境继续安装"
        SAGE_ENV_NAME=""
        return 1
    fi
}

# 激活 conda 环境
activate_conda_environment() {
    local env_name="$1"
    
    echo -e "${INFO} 激活环境: $env_name"
    
    # 验证环境是否真的存在
    if ! conda env list | grep -q "^$env_name "; then
        echo -e "${CROSS} 环境 '$env_name' 不存在，无法激活"
        echo -e "${INFO} 可用的环境："
        conda env list | grep -v "^#" | sed 's/^/  /'
        echo -e "${INFO} 将使用当前环境"
        export PIP_CMD="python3 -m pip"
        export PYTHON_CMD="python3"
        export SAGE_ENV_NAME=""  # 确保导出空值
        return 1
    fi
    
    # 测试 conda run 是否正常工作
    echo -e "${DIM}测试环境: conda run -n $env_name python --version${NC}"
    local test_output=$(conda run -n "$env_name" python --version 2>&1)
    local test_status=$?
    
    if [ $test_status -eq 0 ]; then
        echo -e "${CHECK} 环境测试成功: $test_output"
        
        # 设置环境变量，让子进程使用正确的 conda 环境
        export CONDA_DEFAULT_ENV="$env_name"
        export SAGE_ENV_NAME="$env_name"  # 确保SAGE_ENV_NAME被正确设置和导出
        
        # 更新 pip 命令 - 在CI环境中使用更快的安装方式
        if [ "$CI" = "true" ] || [ "$SAGE_REMOTE_DEPLOY" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ]; then
            # CI环境：使用优化的pip命令和并行安装
            if command -v mamba >/dev/null 2>&1; then
                # 先用mamba安装pip，然后设置普通的pip命令
                conda run -n $env_name mamba install -c conda-forge -y pip
                export PIP_CMD="conda run -n $env_name python -m pip"
                echo -e "${INFO} CI环境：使用mamba安装pip，然后使用标准pip命令"
            else
                # 为CI环境优化的pip命令，简化参数避免重复
                export PIP_CMD="conda run -n $env_name python -m pip"
                echo -e "${INFO} CI环境：使用优化的pip命令"
            fi
            
            # 设置并行构建环境变量
            export PIP_PARALLEL_BUILDS=${PIP_PARALLEL_BUILDS:-4}
            export MAKEFLAGS=${MAKEFLAGS:-"-j4"}
            echo -e "${INFO} 启用并行构建: PIP_PARALLEL_BUILDS=$PIP_PARALLEL_BUILDS, MAKEFLAGS=$MAKEFLAGS"
        else
            # 普通环境：使用标准pip命令
            export PIP_CMD="conda run -n $env_name python -m pip"
        fi
        export PYTHON_CMD="conda run -n $env_name python"
        
        echo -e "${CHECK} 环境已激活"
        echo -e "${DIM}提示: 安装完成后运行 'conda activate $env_name' 来使用 SAGE${NC}"
        return 0
    else
        echo -e "${CROSS} 环境测试失败: $test_output"
        echo -e "${INFO} 环境可能损坏，将使用当前环境"
        export PIP_CMD="python3 -m pip"
        export PYTHON_CMD="python3"
        export SAGE_ENV_NAME=""  # 确保导出空值
        return 1
    fi
}
