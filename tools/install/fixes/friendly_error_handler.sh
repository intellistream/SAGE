#!/bin/bash
# SAGE 用户友好错误处理模块
# 提供清晰的错误说明和解决方案，避免用户误解为SAGE问题

# 导入颜色定义
if [ -f "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
else
    # 备用颜色定义
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    PURPLE='\033[0;35m'
    CYAN='\033[0;36m'
    NC='\033[0m'
    BOLD='\033[1m'
    DIM='\033[2m'
fi

# 错误类型映射
declare -A ERROR_EXPLANATIONS=(
    ["numpy_install_fail"]="NumPy 安装冲突"
    ["torch_cuda_mismatch"]="PyTorch CUDA 版本不匹配"
    ["pip_conda_conflict"]="包管理器冲突"
    ["dependency_resolution"]="依赖解析失败"
    ["disk_space_low"]="磁盘空间不足"
    ["network_timeout"]="网络连接超时"
    ["permission_denied"]="权限不足"
    ["python_version_incompatible"]="Python版本不兼容"
    ["vllm_install_fail"]="vLLM 安装失败"
    ["cuda_not_found"]="CUDA 环境未找到"
)

declare -A ERROR_CAUSES=(
    ["numpy_install_fail"]="这通常是由于系统中存在多个numpy版本或安装记录损坏导致的，属于Python生态系统的常见问题"
    ["torch_cuda_mismatch"]="PyTorch版本与系统CUDA版本不匹配，这是深度学习环境配置的常见问题"
    ["pip_conda_conflict"]="conda和pip同时管理同一个包导致的冲突，这是混合使用包管理器的常见问题"
    ["dependency_resolution"]="不同包之间的版本要求产生冲突，这是复杂Python项目的常见挑战"
    ["disk_space_low"]="安装深度学习库需要较大存储空间，当前磁盘空间不足"
    ["network_timeout"]="网络连接不稳定或PyPI服务器访问缓慢"
    ["permission_denied"]="当前用户没有足够权限安装包到系统目录"
    ["python_version_incompatible"]="当前Python版本与某些包的要求不匹配"
    ["vllm_install_fail"]="vLLM需要特定的CUDA和Python环境，安装要求较为严格"
    ["cuda_not_found"]="系统未正确安装NVIDIA CUDA工具包或驱动"
)

declare -A ERROR_SOLUTIONS=(
    ["numpy_install_fail"]="运行 './quickstart.sh --doctor --fix' 自动修复|手动清理：pip uninstall numpy -y && pip install numpy>=2.0.0|使用新的虚拟环境重新安装"
    ["torch_cuda_mismatch"]="访问 https://pytorch.org 获取正确的安装命令|使用CPU版本：pip install torch --index-url https://download.pytorch.org/whl/cpu|升级CUDA驱动到兼容版本"
    ["pip_conda_conflict"]="统一使用pip管理：conda uninstall <package> -y|或统一使用conda管理：pip uninstall <package> -y|创建新的纯净虚拟环境"
    ["dependency_resolution"]="运行 './quickstart.sh --doctor' 检查环境|清理冲突的包版本|使用 requirements.txt 锁定版本"
    ["disk_space_low"]="清理不必要的文件释放空间|移动到空间更大的目录|使用 pip cache purge 清理缓存"
    ["network_timeout"]="检查网络连接|使用国内镜像：pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/|重试安装命令"
    ["permission_denied"]="使用虚拟环境：python -m venv venv && source venv/bin/activate|添加 --user 参数：pip install --user|使用sudo（不推荐）"
    ["python_version_incompatible"]="使用conda安装兼容版本：conda install python=3.11|检查包的Python版本要求|升级或降级Python版本"
    ["vllm_install_fail"]="确保CUDA >= 11.8|使用预编译版本而非源码编译|检查GPU计算能力是否支持"
    ["cuda_not_found"]="安装NVIDIA驱动|安装CUDA工具包|设置CUDA环境变量"
)

# 检测错误类型
detect_error_type() {
    local error_output="$1"
    local error_type="unknown"
    
    # 转换为小写便于匹配
    local error_lower=$(echo "$error_output" | tr '[:upper:]' '[:lower:]')
    
    # 模式匹配检测错误类型
    if [[ "$error_lower" =~ numpy.*install.*fail|cannot.*uninstall.*numpy|no.*record.*file.*numpy ]]; then
        error_type="numpy_install_fail"
    elif [[ "$error_lower" =~ torch.*cuda.*mismatch|cuda.*not.*available|torch.*gpu ]]; then
        error_type="torch_cuda_mismatch"
    elif [[ "$error_lower" =~ pip.*conda.*conflict|multiple.*package.*managers ]]; then
        error_type="pip_conda_conflict"
    elif [[ "$error_lower" =~ dependency.*resolution|version.*conflict|incompatible.*requirements ]]; then
        error_type="dependency_resolution"
    elif [[ "$error_lower" =~ no.*space.*left|disk.*full|insufficient.*space ]]; then
        error_type="disk_space_low"
    elif [[ "$error_lower" =~ network.*timeout|connection.*timeout|read.*timeout ]]; then
        error_type="network_timeout"
    elif [[ "$error_lower" =~ permission.*denied|access.*denied ]]; then
        error_type="permission_denied"
    elif [[ "$error_lower" =~ python.*version|unsupported.*python ]]; then
        error_type="python_version_incompatible"
    elif [[ "$error_lower" =~ vllm.*install.*fail|vllm.*error ]]; then
        error_type="vllm_install_fail"
    elif [[ "$error_lower" =~ cuda.*not.*found|nvidia.*driver ]]; then
        error_type="cuda_not_found"
    fi
    
    echo "$error_type"
}

# 显示友好的错误信息
show_friendly_error() {
    local error_output="$1"
    local error_type="$2"
    local context="${3:-安装过程中}"
    
    if [ "$error_type" = "unknown" ]; then
        error_type=$(detect_error_type "$error_output")
    fi
    
    echo -e "\n${RED}${BOLD}🚨 $context 遇到问题${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    
    if [ "$error_type" != "unknown" ] && [ -n "${ERROR_EXPLANATIONS[$error_type]}" ]; then
        echo -e "\n${YELLOW}${BOLD}📋 问题类型：${NC}${ERROR_EXPLANATIONS[$error_type]}"
        
        echo -e "\n${BLUE}${BOLD}🔍 问题说明：${NC}"
        echo -e "${DIM}${ERROR_CAUSES[$error_type]}${NC}"
        
        echo -e "\n${PURPLE}${BOLD}💡 重要提醒：${NC}"
        echo -e "${YELLOW}这不是 SAGE 本身的问题，而是 Python 环境配置相关的常见问题。${NC}"
        echo -e "${YELLOW}类似问题在安装其他深度学习框架时也经常遇到。${NC}"
        
        echo -e "\n${GREEN}${BOLD}🔧 推荐解决方案：${NC}"
        IFS='|' read -ra solutions <<< "${ERROR_SOLUTIONS[$error_type]}"
        local counter=1
        for solution in "${solutions[@]}"; do
            echo -e "  ${GREEN}$counter.${NC} $solution"
            ((counter++))
        done
        
        echo -e "\n${CYAN}${BOLD}🤖 自动修复：${NC}"
        echo -e "SAGE 提供了自动诊断和修复工具，可以帮您解决大部分环境问题："
        echo -e "  ${DIM}./quickstart.sh --doctor --fix${NC}"
        
    else
        echo -e "\n${YELLOW}${BOLD}📋 遇到了未知问题${NC}"
        echo -e "${DIM}这可能是一个新的环境配置问题${NC}"
        
        echo -e "\n${GREEN}${BOLD}🔧 通用解决步骤：${NC}"
        echo -e "  ${GREEN}1.${NC} 运行环境诊断：${DIM}./quickstart.sh --doctor${NC}"
        echo -e "  ${GREEN}2.${NC} 检查系统要求：${DIM}Python 3.9-3.12, 5GB+ 磁盘空间${NC}"
        echo -e "  ${GREEN}3.${NC} 使用虚拟环境：${DIM}conda create -n sage-env python=3.11${NC}"
        echo -e "  ${GREEN}4.${NC} 查看详细日志：${DIM}cat install.log${NC}"
    fi
    
    echo -e "\n${BLUE}${BOLD}📚 获取更多帮助：${NC}"
    echo -e "  • 安装故障排除指南：${DIM}https://github.com/intellistream/SAGE/wiki/Troubleshooting${NC}"
    echo -e "  • 环境配置最佳实践：${DIM}https://github.com/intellistream/SAGE/wiki/Environment-Setup${NC}"
    echo -e "  • 提交问题报告：${DIM}https://github.com/intellistream/SAGE/issues${NC}"
    
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    
    # 记录到日志
    if [ -f "$log_file" ]; then
        echo "$(date): [USER_FRIENDLY_ERROR] Type: $error_type, Context: $context" >> "$log_file"
    elif [ -n "${SAGE_DIR:-}" ]; then
        # 如果指定的日志文件不存在，但有SAGE_DIR，则使用默认位置
        mkdir -p "$SAGE_DIR/logs"
        echo "$(date): [USER_FRIENDLY_ERROR] Type: $error_type, Context: $context" >> "$SAGE_DIR/logs/install.log"
    fi
}

# 包装器函数 - 捕获命令错误并提供友好信息
execute_with_friendly_error() {
    local command="$1"
    local context="$2"
    local log_file="${3:-${SAGE_DIR:-$(pwd)/.sage}/logs/install.log}"
    
    echo -e "${DIM}执行：$command${NC}"
    
    # 确保日志目录存在
    mkdir -p "$(dirname "$log_file")"
    
    # 执行命令并捕获输出
    local temp_output="${SAGE_DIR:-$(pwd)/.sage}/tmp/error_output_$(date +%s).tmp"
    mkdir -p "$(dirname "$temp_output")"
    local exit_code
    
    if eval "$command" 2>&1 | tee "$temp_output"; then
        exit_code=0
    else
        exit_code=$?
    fi
    
    # 如果命令失败，显示友好错误信息
    if [ $exit_code -ne 0 ]; then
        local error_output=$(cat "$temp_output")
        show_friendly_error "$error_output" "unknown" "$context"
        
        # 询问是否继续
        echo -e "\n${YELLOW}是否尝试继续安装？${NC} ${DIM}[y/N]${NC}"
        read -r -t 30 response || response="n"
        response=${response,,}
        
        if [[ ! "$response" =~ ^(y|yes)$ ]]; then
            echo -e "${YELLOW}安装已取消${NC}"
            cleanup_temp_files "$temp_output"
            exit $exit_code
        fi
    fi
    
    cleanup_temp_files "$temp_output"
    return $exit_code
}

# 清理临时文件
cleanup_temp_files() {
    local temp_file="$1"
    if [ -f "$temp_file" ]; then
        rm -f "$temp_file"
    fi
    
    # 清理老的临时文件
    if [ -d "${SAGE_DIR:-$(pwd)/.sage}/tmp" ]; then
        find "${SAGE_DIR:-$(pwd)/.sage}/tmp" -name "error_output_*.tmp" -mtime +1 -delete 2>/dev/null || true
    fi
}

# 检查并报告安装成功
report_success() {
    local component="$1"
    echo -e "\n${GREEN}${BOLD}✅ $component 安装成功！${NC}"
    echo -e "${DIM}感谢您耐心等待安装完成${NC}"
}

# 检查并报告部分成功
report_partial_success() {
    local component="$1"
    local issue="$2"
    
    echo -e "\n${YELLOW}${BOLD}⚠️  $component 安装基本完成${NC}"
    echo -e "${YELLOW}但存在一些小问题：$issue${NC}"
    echo -e "${DIM}这不会影响 SAGE 的核心功能${NC}"
}

# 显示安装进度和用户友好提示
show_installation_progress() {
    local step="$1"
    local total_steps="$2"
    local current_task="$3"
    
    local progress=$((step * 100 / total_steps))
    local bar_length=30
    local filled_length=$((progress * bar_length / 100))
    
    local bar=""
    for ((i=0; i<filled_length; i++)); do
        bar+="█"
    done
    for ((i=filled_length; i<bar_length; i++)); do
        bar+="░"
    done
    
    echo -e "\n${BLUE}${BOLD}📦 安装进度 [$step/$total_steps]${NC}"
    echo -e "${BLUE}[$bar] $progress%${NC}"
    echo -e "${DIM}当前步骤：$current_task${NC}"
    
    # 根据步骤提供相应的用户提示
    case $step in
        1)
            echo -e "${DIM}正在检查 Python 环境和基础依赖...${NC}"
            ;;
        2)
            echo -e "${DIM}正在安装核心包，这可能需要几分钟...${NC}"
            ;;
        3)
            echo -e "${DIM}正在配置深度学习环境...${NC}"
            ;;
        4)
            echo -e "${DIM}正在进行最终验证和清理...${NC}"
            ;;
    esac
}

# 处理用户中断
handle_user_interrupt() {
    echo -e "\n\n${YELLOW}${BOLD}⚠️  检测到用户中断 (Ctrl+C)${NC}"
    echo -e "${BLUE}正在安全清理临时文件...${NC}"
    
    # 清理可能的临时文件
    if [ -d "${SAGE_DIR:-$(pwd)/.sage}/tmp" ]; then
        find "${SAGE_DIR:-$(pwd)/.sage}/tmp" -name "sage_install_*" -type f -delete 2>/dev/null || true
        find "${SAGE_DIR:-$(pwd)/.sage}/tmp" -name "error_output_*.tmp" -type f -delete 2>/dev/null || true
    fi
    
    # 备用清理
    find /tmp -name "sage_install_*" -type f -delete 2>/dev/null || true
    
    echo -e "${YELLOW}安装已被用户取消${NC}"
    echo -e "${DIM}您可以稍后重新运行 ./quickstart.sh 继续安装${NC}"
    exit 130
}

# 设置中断处理
trap 'handle_user_interrupt' INT TERM

# 导出函数供其他脚本使用
export -f show_friendly_error
export -f execute_with_friendly_error
export -f report_success
export -f report_partial_success
export -f show_installation_progress
export -f detect_error_type