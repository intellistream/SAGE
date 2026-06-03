#!/bin/bash
# SAGE 安装前环境预检查模块
# 实现 2.1 要求：检查磁盘空间、网络连接、内存、CUDA 可用性

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../ui/colors.sh"
# 导入 Conda 安装引导模块
source "$(dirname "${BASH_SOURCE[0]}")/conda_guide.sh"

# 最小要求常量

# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
CUDA_PATH="${CUDA_PATH:-}"
CUDA_HOME="${CUDA_HOME:-}"
# ============================================================================

MIN_DISK_SPACE_GB=5
MIN_MEMORY_GB=4
MIN_AVAILABLE_MEMORY_GB=2

# 检查磁盘空间
check_disk_space() {
    local required_gb="${1:-$MIN_DISK_SPACE_GB}"

    echo -e "${BLUE}🔍 检查磁盘空间...${NC}"

    # 获取当前目录可用空间（GB）
    local available_space_kb=$(df . | awk 'NR==2 {print $4}')
    local available_space_gb=$((available_space_kb / 1024 / 1024))

    echo -e "${DIM}   可用空间: ${available_space_gb}GB (需要: ${required_gb}GB)${NC}"

    if [ "$available_space_gb" -ge "$required_gb" ]; then
        echo -e "${GREEN}   ✅ 磁盘空间充足${NC}"
        return 0
    else
        echo -e "${RED}   ❌ 磁盘空间不足${NC}"
        echo -e "${YELLOW}   建议操作:${NC}"
        echo -e "${DIM}   • 清理不必要的文件释放空间${NC}"
        echo -e "${DIM}   • 运行: pip cache purge 清理缓存${NC}"
        echo -e "${DIM}   • 移动到空间更大的目录${NC}"
        return 1
    fi
}

# 检查网络连接性
check_network_connectivity() {
    echo -e "${BLUE}🔍 检查网络连接...${NC}"

    local test_urls=(
        "https://pypi.org/simple/"
        "https://files.pythonhosted.org"
        "https://github.com"
    )

    local failed_urls=()

    for url in "${test_urls[@]}"; do
        echo -e "${DIM}   测试连接: $url${NC}"

        if curl -s --connect-timeout 5 --max-time 10 "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}   ✅ $url 可访问${NC}"
        elif wget -q --spider --tries=1 --dns-timeout=5 --connect-timeout=5 --read-timeout=10 "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}   ✅ $url 可访问${NC}"
        else
            echo -e "${RED}   ❌ $url 无法访问${NC}"
            failed_urls+=("$url")
        fi
    done

    if [ ${#failed_urls[@]} -eq 0 ]; then
        echo -e "${GREEN}   ✅ 网络连接正常${NC}"
        return 0
    else
        echo -e "${YELLOW}   ⚠️  部分网络连接失败${NC}"
        echo -e "${YELLOW}   建议操作:${NC}"
        echo -e "${DIM}   • 检查网络连接${NC}"
        echo -e "${DIM}   • 使用国内镜像: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/${NC}"
        echo -e "${DIM}   • 配置代理设置${NC}"
        return 1
    fi
}

# 检查内存
check_memory() {
    local required_total_gb="${1:-$MIN_MEMORY_GB}"
    local required_available_gb="${2:-$MIN_AVAILABLE_MEMORY_GB}"

    echo -e "${BLUE}🔍 检查内存状态...${NC}"

    # 获取内存信息（MB）
    local mem_info=$(free -m)
    local total_mem_mb=$(echo "$mem_info" | awk 'NR==2{print $2}')
    local available_mem_mb=$(echo "$mem_info" | awk 'NR==2{print $7}')

    # 如果 available 列不存在，使用 free 列
    if [ -z "$available_mem_mb" ] || [ "$available_mem_mb" = "" ]; then
        available_mem_mb=$(echo "$mem_info" | awk 'NR==2{print $4}')
    fi

    local total_mem_gb=$((total_mem_mb / 1024))
    local available_mem_gb=$((available_mem_mb / 1024))

    echo -e "${DIM}   总内存: ${total_mem_gb}GB (需要: ${required_total_gb}GB)${NC}"
    echo -e "${DIM}   可用内存: ${available_mem_gb}GB (建议: ${required_available_gb}GB)${NC}"

    local memory_ok=true

    if [ "$total_mem_gb" -lt "$required_total_gb" ]; then
        echo -e "${RED}   ❌ 总内存不足${NC}"
        memory_ok=false
    else
        echo -e "${GREEN}   ✅ 总内存充足${NC}"
    fi

    if [ "$available_mem_gb" -lt "$required_available_gb" ]; then
        echo -e "${YELLOW}   ⚠️  可用内存偏低${NC}"
        echo -e "${DIM}   建议关闭其他应用程序释放内存${NC}"
    else
        echo -e "${GREEN}   ✅ 可用内存充足${NC}"
    fi

    if [ "$memory_ok" = true ]; then
        return 0
    else
        echo -e "${YELLOW}   建议操作:${NC}"
        echo -e "${DIM}   • 关闭不必要的应用程序${NC}"
        echo -e "${DIM}   • 增加系统内存${NC}"
        echo -e "${DIM}   • 使用交换文件增加虚拟内存${NC}"
        return 1
    fi
}

# 检查是否在 conda base 环境
check_conda_base_environment() {
    echo -e "${BLUE}🔍 检查 Conda 环境...${NC}"

    # 检查是否使用 conda
    if [ -z "$CONDA_DEFAULT_ENV" ]; then
        echo -e "${DIM}   未检测到 Conda 环境${NC}"
        return 0  # 不使用 conda，跳过检查
    fi

    # 检查是否在 base 环境
    if [ "$CONDA_DEFAULT_ENV" = "base" ]; then
        echo -e "${YELLOW}   ⚠️  检测到您正在使用 Conda base 环境${NC}"
        echo -e "${RED}   ❌ 不建议在 base 环境中安装 SAGE${NC}"
        echo ""
        echo -e "${YELLOW}   为什么不应该使用 base 环境：${NC}"
        echo -e "${DIM}   • 可能导致环境污染和依赖冲突${NC}"
        echo -e "${DIM}   • 影响其他项目的正常运行${NC}"
        echo -e "${DIM}   • 难以卸载和清理${NC}"
        echo ""
        echo -e "${GREEN}   建议操作：${NC}"
        echo -e "${DIM}   1. 创建专用 sage 环境：${NC}"
        echo -e "      ${CYAN}conda create -n sage python=3.11 -y${NC}"
        echo -e "      ${CYAN}conda activate sage${NC}"
        echo -e ""
        echo -e "${DIM}   2. 然后重新运行安装脚本：${NC}"
        echo -e "      ${CYAN}./quickstart.sh --dev --yes${NC}"
        echo ""

        # 检查是否在 CI 环境
        if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ]; then
            echo -e "${YELLOW}   ⚠️  检测到 CI 环境，跳过交互式提示${NC}"
            return 1  # CI 环境返回警告但继续
        fi

        # 提供交互式选项（仅在交互式终端）
        if [ -t 0 ]; then  # 只在交互式终端中提示
            read -p "是否自动创建并切换到 sage 环境? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${BLUE}🔧 正在创建 sage 环境...${NC}"
                if conda create -n sage python=3.11 -y; then
                    echo -e "${GREEN}✅ sage 环境创建成功${NC}"
                    echo ""
                    echo -e "${YELLOW}⚠️  请手动激活 sage 环境后重新运行安装：${NC}"
                    echo -e "   ${CYAN}conda activate sage${NC}"
                    echo -e "   ${CYAN}./quickstart.sh --dev --yes${NC}"
                    exit 0
                else
                    echo -e "${RED}❌ 创建环境失败${NC}"
                    return 1
                fi
            else
                echo -e "${YELLOW}⚠️  继续在 base 环境安装可能导致问题${NC}"
                read -p "确定要继续吗? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo -e "${YELLOW}已取消安装${NC}"
                    exit 0
                fi
            fi
        else
            # 非交互且非CI模式，仅警告
            echo -e "${YELLOW}   ⚠️  非交互模式，请手动切换到专用环境${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}   ✅ 使用专用环境: $CONDA_DEFAULT_ENV${NC}"
        return 0
    fi
}

# 检查 CUDA 可用性
check_cuda_availability() {
    echo -e "${BLUE}🔍 检查 CUDA 环境...${NC}"

    local cuda_available=false
    local driver_version=""
    local cuda_version=""
    local has_gpu=false

    # 检查 NVIDIA 驱动
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits 2>/dev/null | head -1)
            cuda_version=$(nvidia-smi | grep "CUDA Version:" | awk '{print $9}' 2>/dev/null)
            has_gpu=true
            cuda_available=true
            echo -e "${GREEN}   ✅ NVIDIA 驱动已安装 (版本: ${driver_version})${NC}"
            if [ -n "$cuda_version" ]; then
                echo -e "${GREEN}   ✅ CUDA 运行时版本: ${cuda_version}${NC}"
            fi
        else
            echo -e "${RED}   ❌ nvidia-smi 命令失败${NC}"
        fi
    else
        echo -e "${YELLOW}   ⚠️  未找到 nvidia-smi 命令${NC}"
    fi

    # 检查 CUDA 环境变量
    if [ -n "$CUDA_HOME" ] || [ -n "$CUDA_PATH" ]; then
        echo -e "${GREEN}   ✅ CUDA 环境变量已设置${NC}"
        echo -e "${DIM}   CUDA_HOME: ${CUDA_HOME}${NC}"
        echo -e "${DIM}   CUDA_PATH: ${CUDA_PATH}${NC}"
    else
        echo -e "${YELLOW}   ⚠️  CUDA 环境变量未设置${NC}"
    fi

    if [ "$cuda_available" = true ]; then
        echo -e "${GREEN}   ✅ CUDA 环境可用，支持 GPU 加速${NC}"
        return 0
    else
        echo -e "${YELLOW}   ⚠️  CUDA 环境不完整${NC}"
        echo -e "${YELLOW}   建议操作:${NC}"
        echo -e "${DIM}   • 安装 NVIDIA 驱动: apt install nvidia-driver-XXX${NC}"
        echo -e "${DIM}   • 安装 CUDA 工具包: https://developer.nvidia.com/cuda-downloads${NC}"
        echo -e "${DIM}   • 设置环境变量: export CUDA_HOME=/usr/local/cuda${NC}"
        echo -e "${DIM}   • 注意: 没有 CUDA 也可安装，但无法使用 GPU 加速${NC}"
        return 1
    fi
}

# 创建检查报告
create_precheck_report() {
    local report_file="$1"
    local disk_status="$2"
    local network_status="$3"
    local memory_status="$4"
    local cuda_status="$5"

    mkdir -p "$(dirname "$report_file")"

    cat > "$report_file" << EOF
# SAGE 安装前环境检查报告
生成时间: $(date)

## 检查结果摘要
- 磁盘空间: $disk_status
- 网络连接: $network_status
- 内存状态: $memory_status
- CUDA 环境: $cuda_status

## 系统信息
- 操作系统: $(uname -s)
- 内核版本: $(uname -r)
- 架构: $(uname -m)
- Python 版本: $(python3 --version 2>/dev/null || echo "未安装")

## 详细信息
### 磁盘使用情况
$(df -h .)

### 内存使用情况
$(free -h)

### NVIDIA 信息
$(nvidia-smi 2>/dev/null || echo "NVIDIA 驱动未安装或不可用")
EOF

    echo -e "${DIM}   📋 检查报告已保存: $report_file${NC}"
}

# 运行完整的环境预检查
run_environment_prechecks() {
    local skip_cuda="${1:-false}"
    local report_file="${2:-.sage/logs/environment_precheck.log}"

    echo -e "${BLUE}${BOLD}🔍 开始环境预检查...${NC}"
    echo ""

    local all_checks_passed=true
    local disk_status="UNKNOWN"
    local network_status="UNKNOWN"
    local memory_status="UNKNOWN"
    local cuda_status="UNKNOWN"
    local conda_env_status="UNKNOWN"

    # 检查 Conda 环境（最优先）：未安装 / base / 未激活 / 正常
    # 若 apply_defaults 中已交互完成，则跳过重复询问
    if [ "${_SAGE_CONDA_ENV_CHECKED:-false}" = "true" ]; then
        echo -e "${GREEN}   ✅ Conda 环境检查已完成（跳过重复检查）${NC}"
        conda_env_status="PASS"
    elif check_conda_environment; then
        conda_env_status="PASS"
    else
        conda_env_status="WARN"
        # 警告但不阻止安装（用户可能选择继续）
    fi
    echo ""

    # 检查磁盘空间
    if check_disk_space; then
        disk_status="PASS"
    else
        disk_status="FAIL"
        all_checks_passed=false
    fi
    echo ""

    # 检查网络连接
    if check_network_connectivity; then
        network_status="PASS"
    else
        network_status="WARN"
        # 网络问题不阻止安装
    fi
    echo ""

    # 检查内存
    if check_memory; then
        memory_status="PASS"
    else
        memory_status="WARN"
        # 内存不足给警告但不阻止安装
    fi
    echo ""

    # 检查 CUDA（可选）
    if [ "$skip_cuda" != "true" ]; then
        if check_cuda_availability; then
            cuda_status="PASS"
        else
            cuda_status="OPTIONAL"
            # CUDA 不可用不影响基础安装
        fi
        echo ""
    else
        cuda_status="SKIPPED"
    fi

    # 生成检查报告
    create_precheck_report "$report_file" "$disk_status" "$network_status" "$memory_status" "$cuda_status"
    echo ""

    # 显示总结
    if [ "$all_checks_passed" = true ]; then
        echo -e "${GREEN}${BOLD}✅ 环境预检查通过，可以开始安装${NC}"
        return 0
    else
        echo -e "${YELLOW}${BOLD}⚠️  环境预检查发现问题，但可以尝试继续安装${NC}"
        echo -e "${DIM}建议: 解决上述问题后再安装，以获得更好的体验${NC}"
        return 1
    fi
}

# 快速检查（仅关键项目）
run_quick_prechecks() {
    echo -e "${BLUE}🔍 快速环境检查...${NC}"

    local critical_failed=false

    # 只检查关键的磁盘空间
    if ! check_disk_space; then
        critical_failed=true
    fi

    if [ "$critical_failed" = true ]; then
        echo -e "${RED}❌ 关键环境检查失败${NC}"
        return 1
    else
        echo -e "${GREEN}✅ 基础环境检查通过${NC}"
        return 0
    fi
}
