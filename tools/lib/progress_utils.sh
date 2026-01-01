#!/usr/bin/env bash
# ============================================================================
# Progress Utilities - 统一的进度显示工具集
# ============================================================================
# 提供多种进度显示方式：
# 1. 进度条（百分比）
# 2. 旋转器（spinner，适合长时间任务）
# 3. 带估算时间的进度条
# 4. 安装步骤进度显示
# ============================================================================

set -euo pipefail

# 颜色定义（如果未加载 logging.sh）
if [ -z "${BLUE:-}" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    DIM='\033[2m'
    BOLD='\033[1m'
    NC='\033[0m'
    CHECK='✓'
    CROSS='✗'
    GEAR='⚙'
    PACKAGE='📦'
fi

# ============================================================================
# 1. 简单进度条（原 logging.sh 中的实现）
# ============================================================================
# 用法：print_progress 50 100 "正在下载..."
print_progress() {
    local current=$1
    local total=$2
    local description="${3:-Processing}"
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    printf "\r${BLUE}[INFO]${NC} $description ["
    printf "%${filled}s" | tr ' ' '#'
    printf "%${empty}s" | tr ' ' '-'
    printf "] %d%%" $percentage

    if [ $current -eq $total ]; then
        echo ""
    fi
}

# ============================================================================
# 2. 旋转器（spinner，适合不确定时长的任务）
# ============================================================================
# 用法：
#   long_running_command &
#   show_spinner $! "正在执行任务..."
show_spinner() {
    local pid=$1
    local message="${2:-Processing}"
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

    # 隐藏光标
    tput civis 2>/dev/null || true

    while kill -0 "$pid" 2>/dev/null; do
        local temp=${spinstr#?}
        printf "\r${BLUE}%c${NC} %s" "$spinstr" "$message"
        local spinstr=$temp${spinstr%"$temp"}
        sleep 0.1
    done

    # 等待进程结束并获取退出码
    wait "$pid" 2>/dev/null
    local exit_code=$?

    # 显示光标
    tput cnorm 2>/dev/null || true

    if [ $exit_code -eq 0 ]; then
        printf "\r${GREEN}${CHECK}${NC} %s\n" "$message"
    else
        printf "\r${RED}${CROSS}${NC} %s (失败，退出码: $exit_code)\n" "$message"
    fi

    return $exit_code
}

# ============================================================================
# 3. 带时间估算的进度条（用于已知步骤数的安装过程）
# ============================================================================
# 用法：show_installation_progress 2 5 "安装核心依赖"
show_installation_progress() {
    local step="$1"
    local total_steps="$2"
    local current_task="${3:-Processing}"

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

    echo -e "\n${BLUE}${BOLD}${PACKAGE} 安装进度 [$step/$total_steps]${NC}"
    echo -e "${BLUE}[$bar] $progress%${NC}"
    echo -e "${DIM}当前步骤：$current_task${NC}"
}

# ============================================================================
# 4. 内联进度指示器（不换行，适合实时更新）
# ============================================================================
# 用法：
#   for i in {1..100}; do
#       show_inline_progress $i 100 "下载中"
#       sleep 0.1
#   done
show_inline_progress() {
    local current=$1
    local total=$2
    local prefix="${3:-Progress}"
    local percentage=$((current * 100 / total))

    # 简洁的进度显示
    printf "\r${BLUE}${GEAR}${NC} %s: %d%% " "$prefix" "$percentage"

    if [ $current -eq $total ]; then
        printf "${GREEN}${CHECK}${NC}\n"
    fi
}

# ============================================================================
# 5. 长时间任务进度提示（定期输出保活信息）
# ============================================================================
# 用法：
#   long_task_with_keepalive "安装系统依赖" 60 "apt-get install -y build-essential"
# 参数：
#   $1 - 任务描述
#   $2 - 保活间隔（秒，默认30秒）
#   $3... - 要执行的命令
long_task_with_keepalive() {
    local task_desc="$1"
    local keepalive_interval="${2:-30}"
    shift 2
    local command=("$@")

    echo -e "${BLUE}${GEAR}${NC} 开始：$task_desc"
    echo -e "${DIM}这可能需要几分钟，请耐心等待...${NC}"

    # 启动后台任务
    "${command[@]}" &
    local pid=$!

    local elapsed=0
    local dot_count=0

    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
        elapsed=$((elapsed + 1))
        dot_count=$((dot_count + 1))

        # 每秒显示一个点
        if [ $dot_count -le 3 ]; then
            printf "."
        else
            dot_count=0
            printf "\r${DIM}   运行中 %ds${NC}" "$elapsed"
        fi

        # 定期显示保活信息
        if [ $((elapsed % keepalive_interval)) -eq 0 ]; then
            printf "\n${DIM}   仍在进行中... (已运行 %ds)${NC}\n" "$elapsed"
        fi
    done

    # 获取退出码
    wait "$pid" 2>/dev/null
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}${CHECK}${NC} 完成：$task_desc (耗时 ${elapsed}s)"
    else
        echo -e "\n${RED}${CROSS}${NC} 失败：$task_desc (退出码: $exit_code, 耗时 ${elapsed}s)"
    fi

    return $exit_code
}

# ============================================================================
# 6. 简化的后台任务进度显示（最常用）
# ============================================================================
# 用法：
#   run_with_progress "安装 Node.js" "conda install -y nodejs"
# 这是最简单的接口，自动处理后台任务和进度显示
run_with_progress() {
    local task_desc="$1"
    shift
    local command=("$@")

    echo -e "${BLUE}${GEAR}${NC} $task_desc..."

    # 执行命令到后台，捕获输出
    local output
    output=$("${command[@]}" 2>&1) &
    local pid=$!

    # 显示 spinner
    show_spinner "$pid" "$task_desc"
    local exit_code=$?

    # 如果失败，显示输出
    if [ $exit_code -ne 0 ]; then
        echo -e "${DIM}--- 命令输出 ---${NC}"
        echo "$output"
        echo -e "${DIM}--- 输出结束 ---${NC}"
    fi

    return $exit_code
}

# ============================================================================
# 导出函数（可选，如果使用 source 加载）
# ============================================================================
export -f print_progress 2>/dev/null || true
export -f show_spinner 2>/dev/null || true
export -f show_installation_progress 2>/dev/null || true
export -f show_inline_progress 2>/dev/null || true
export -f long_task_with_keepalive 2>/dev/null || true
export -f run_with_progress 2>/dev/null || true
