#!/bin/bash
# SAGE 进度条显示模块
# 纯 Bash 实现，无需外部依赖

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/colors.sh"

# 进度条配置
PROGRESS_BAR_WIDTH=50
PROGRESS_BAR_CHAR="█"
PROGRESS_BAR_EMPTY_CHAR="░"

# ============================================================================
# 基础进度条
# ============================================================================

# 显示进度条
# 用法: show_progress_bar <current> <total> [prefix]
show_progress_bar() {
    local current="$1"
    local total="$2"
    local prefix="${3:-Progress}"

    # 计算百分比
    local percent=$((current * 100 / total))

    # 计算填充的字符数
    local filled=$((current * PROGRESS_BAR_WIDTH / total))
    local empty=$((PROGRESS_BAR_WIDTH - filled))

    # 构建进度条
    local bar=""
    for ((i=0; i<filled; i++)); do
        bar+="$PROGRESS_BAR_CHAR"
    done
    for ((i=0; i<empty; i++)); do
        bar+="$PROGRESS_BAR_EMPTY_CHAR"
    done

    # 显示进度条（覆盖同一行）
    printf "\r${BLUE}${prefix}:${NC} [${GREEN}${bar}${NC}] ${BOLD}%3d%%${NC} (%d/%d)" "$percent" "$current" "$total"
}

# 完成进度条（换行）
finish_progress_bar() {
    echo ""
}

# ============================================================================
# 阶段式进度条
# ============================================================================

# 阶段进度跟踪
declare -A PHASE_PROGRESS
CURRENT_PHASE=""
TOTAL_PHASES=0

# 初始化阶段进度
# 用法: init_phase_progress <phase1> <phase2> ...
init_phase_progress() {
    TOTAL_PHASES=$#
    local phase_index=0

    for phase in "$@"; do
        PHASE_PROGRESS[$phase]=$phase_index
        ((phase_index++))
    done
}

# 设置当前阶段
# 用法: set_current_phase <phase_name>
set_current_phase() {
    CURRENT_PHASE="$1"
}

# 显示阶段进度
# 用法: show_phase_progress
show_phase_progress() {
    if [ -z "$CURRENT_PHASE" ]; then
        return
    fi

    local current_index=${PHASE_PROGRESS[$CURRENT_PHASE]}
    local percent=$(((current_index + 1) * 100 / TOTAL_PHASES))

    # 构建进度条
    local filled=$(((current_index + 1) * PROGRESS_BAR_WIDTH / TOTAL_PHASES))
    local empty=$((PROGRESS_BAR_WIDTH - filled))

    local bar=""
    for ((i=0; i<filled; i++)); do
        bar+="$PROGRESS_BAR_CHAR"
    done
    for ((i=0; i<empty; i++)); do
        bar+="$PROGRESS_BAR_EMPTY_CHAR"
    done

    printf "\r${BLUE}安装进度:${NC} [${GREEN}${bar}${NC}] ${BOLD}%3d%%${NC} - ${CYAN}%s${NC}" "$percent" "$CURRENT_PHASE"
}

# ============================================================================
# 旋转加载动画
# ============================================================================

# 旋转动画字符
SPINNER_CHARS=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
SPINNER_INDEX=0

# 显示旋转动画
# 用法: show_spinner <message>
show_spinner() {
    local message="$1"

    printf "\r${BLUE}${SPINNER_CHARS[$SPINNER_INDEX]}${NC} ${message}"

    SPINNER_INDEX=$(((SPINNER_INDEX + 1) % ${#SPINNER_CHARS[@]}))
}

# 停止旋转动画
stop_spinner() {
    printf "\r${GREEN}✓${NC} "
}

# ============================================================================
# 下载进度条
# ============================================================================

# 显示下载进度
# 用法: show_download_progress <downloaded_mb> <total_mb> <speed_mbps>
show_download_progress() {
    local downloaded="$1"
    local total="$2"
    local speed="${3:-0}"

    local percent=$((downloaded * 100 / total))

    # 计算剩余时间
    local eta="--:--"
    if [ "$speed" != "0" ] && [ "$(echo "$speed > 0" | bc 2>/dev/null || echo 0)" = "1" ]; then
        local remaining=$((total - downloaded))
        local eta_seconds=$(echo "scale=0; $remaining / $speed" | bc 2>/dev/null || echo 0)
        eta=$(printf "%02d:%02d" $((eta_seconds / 60)) $((eta_seconds % 60)))
    fi

    # 构建进度条
    local filled=$((downloaded * PROGRESS_BAR_WIDTH / total))
    local empty=$((PROGRESS_BAR_WIDTH - filled))

    local bar=""
    for ((i=0; i<filled; i++)); do
        bar+="$PROGRESS_BAR_CHAR"
    done
    for ((i=0; i<empty; i++)); do
        bar+="$PROGRESS_BAR_EMPTY_CHAR"
    done

    printf "\r${BLUE}下载:${NC} [${GREEN}${bar}${NC}] ${BOLD}%3d%%${NC} %.1fMB/%.1fMB @ %.1fMB/s ETA: %s" \
        "$percent" "$downloaded" "$total" "$speed" "$eta"
}

# ============================================================================
# 包安装进度
# ============================================================================

# 显示包安装进度
# 用法: show_package_install_progress <current_package> <total_packages> <package_name>
show_package_install_progress() {
    local current="$1"
    local total="$2"
    local package_name="${3:-package}"

    local percent=$((current * 100 / total))

    # 构建进度条
    local filled=$((current * PROGRESS_BAR_WIDTH / total))
    local empty=$((PROGRESS_BAR_WIDTH - filled))

    local bar=""
    for ((i=0; i<filled; i++)); do
        bar+="$PROGRESS_BAR_CHAR"
    done
    for ((i=0; i<empty; i++)); do
        bar+="$PROGRESS_BAR_EMPTY_CHAR"
    done

    # 截断包名（如果太长）
    if [ ${#package_name} -gt 30 ]; then
        package_name="${package_name:0:27}..."
    fi

    printf "\r${BLUE}安装包:${NC} [${GREEN}${bar}${NC}] ${BOLD}%3d%%${NC} (%d/%d) ${CYAN}%s${NC}" \
        "$percent" "$current" "$total" "$package_name"
}

# ============================================================================
# 实用函数
# ============================================================================

# 清除当前行
clear_line() {
    printf "\r\033[K"
}

# 显示完成标记
show_completion() {
    local message="${1:-Complete}"
    clear_line
    echo -e "${GREEN}✅ ${message}${NC}"
}

# 显示错误标记
show_error() {
    local message="${1:-Failed}"
    clear_line
    echo -e "${RED}❌ ${message}${NC}"
}

# ============================================================================
# 使用示例（仅在直接执行时显示）
# ============================================================================

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    echo "进度条模块使用示例："
    echo ""

    # 示例 1: 基础进度条
    echo "1. 基础进度条:"
    for i in {1..100}; do
        show_progress_bar $i 100 "处理中"
        sleep 0.02
    done
    finish_progress_bar
    echo ""

    # 示例 2: 阶段进度
    echo "2. 阶段进度:"
    init_phase_progress "环境准备" "依赖安装" "包安装" "验证测试" "清理完成"

    for phase in "环境准备" "依赖安装" "包安装" "验证测试" "清理完成"; do
        set_current_phase "$phase"
        for i in {1..20}; do
            show_phase_progress
            sleep 0.05
        done
    done
    finish_progress_bar
    echo ""

    # 示例 3: 旋转动画
    echo "3. 旋转动画:"
    for i in {1..50}; do
        show_spinner "正在处理..."
        sleep 0.1
    done
    stop_spinner
    echo "处理完成"
    echo ""

    # 示例 4: 包安装进度
    echo "4. 包安装进度:"
    packages=("numpy" "pandas" "torch" "transformers" "scikit-learn")
    for i in "${!packages[@]}"; do
        show_package_install_progress $((i+1)) ${#packages[@]} "${packages[$i]}"
        sleep 0.5
    done
    finish_progress_bar
    echo ""

    show_completion "所有示例演示完成"
fi
