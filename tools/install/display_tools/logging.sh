#!/bin/bash
# 增强的日志记录工具
# 提供结构化、分级的日志记录功能

source "$(dirname "${BASH_SOURCE[0]}")/colors.sh"

# 日志级别

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
# ============================================================================

LOG_LEVEL_DEBUG=0
LOG_LEVEL_INFO=1
LOG_LEVEL_WARN=2
LOG_LEVEL_ERROR=3

# 将字符串日志级别转换为数字
_parse_log_level() {
    local level="$1"
    case "$level" in
        0|DEBUG|debug) echo 0 ;;
        1|INFO|info)   echo 1 ;;
        2|WARN|warn)   echo 2 ;;
        3|ERROR|error) echo 3 ;;
        *)             echo 1 ;;  # 默认 INFO
    esac
}

# 当前日志级别（默认 INFO，支持字符串或数字）
CURRENT_LOG_LEVEL=$(_parse_log_level "${SAGE_LOG_LEVEL:-1}")

# 日志文件路径（全局变量，由主安装脚本设置）
SAGE_INSTALL_LOG="${SAGE_INSTALL_LOG:-.sage/logs/install.log}"

# 确保日志目录存在
_ensure_log_dir() {
    local log_dir=$(dirname "${SAGE_INSTALL_LOG:-}")
    mkdir -p "$log_dir" 2>/dev/null || true
}

# 格式化时间戳
_log_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# 安全转义 JSON 文本
_escape_json() {
    local raw="$1"
    printf '%s' "$raw" \
        | sed -e 's/\\/\\\\/g' \
               -e 's/"/\\"/g' \
               -e 's/\t/\\t/g' \
               -e ':a;N;$!ba;s/\n/\\n/g'
}

# 写入日志文件（JSON 格式）
_write_log() {
    local level="$1"
    local message="$2"
    local context="${3:-}"
    local phase="${4:-}"

    _ensure_log_dir

    local escaped_message=$(_escape_json "$message")
    local escaped_context=$(_escape_json "$context")
    local escaped_phase=$(_escape_json "$phase")

    local json_log=$(printf '{"timestamp": "%s", "level": "%s", "context": "%s", "phase": "%s", "message": "%s"}' \
        "$(_log_timestamp)" \
        "$level" \
        "$escaped_context" \
        "$escaped_phase" \
        "$escaped_message")

    echo "$json_log" >> "${SAGE_INSTALL_LOG:-}"
}

# DEBUG 级别日志（详细调试信息）
log_debug() {
    local message="$1"
    local context="${2:-}"
    local phase="${3:-}"

    if [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_DEBUG ]; then
        echo -e "${DIM}[DEBUG] $message${NC}" >&2
    fi

    _write_log "DEBUG" "$message" "$context" "$phase"
}

# INFO 级别日志（一般信息）
log_info() {
    local message="$1"
    local context="${2:-}"
    local show_console="${3:-true}"
    local phase="${4:-}"

    if [ "$show_console" = "true" ] && [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_INFO ]; then
        echo -e "${DIM}[INFO] $message${NC}"
    fi

    _write_log "INFO" "$message" "$context" "$phase"
}

# WARN 级别日志（警告）
log_warn() {
    local message="$1"
    local context="${2:-}"
    local phase="${3:-}"

    if [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_WARN ]; then
        echo -e "${YELLOW}[WARN] $message${NC}" >&2
    fi

    _write_log "WARN" "$message" "$context" "$phase"
}

# ERROR 级别日志（错误）
log_error() {
    local message="$1"
    local context="${2:-}"
    local phase="${3:-}"

    if [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_ERROR ]; then
        echo -e "${RED}[ERROR] $message${NC}" >&2
    fi

    _write_log "ERROR" "$message" "$context" "$phase"
}

# SUCCESS 级别日志（成功）
log_success() {
    local message="$1"
    local context="${2:-}"
    local phase="${3:-}"

    if [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_INFO ]; then
        echo -e "${GREEN}[SUCCESS] $message${NC}"
    fi

    _write_log "SUCCESS" "$message" "$context" "$phase"
}

# 记录命令执行（带返回值和输出）
log_command() {
    local context="$1"
    local phase="$2"
    shift 2
    local cmd="$@"

    log_debug "执行命令: $cmd" "$context" "$phase"

    # 创建临时文件存储输出
    local temp_output=$(mktemp)
    local exit_code=0

    # 执行命令并捕获输出和返回值
    if eval "$cmd" > "$temp_output" 2>&1; then
        exit_code=0
        log_debug "命令成功 (exit=$exit_code): $cmd" "$context" "$phase"

        # 如果输出不为空，记录前10行
        if [ -s "$temp_output" ]; then
            local output_preview=$(head -10 "$temp_output")
            log_debug "命令输出预览:\n$output_preview" "$context" "$phase"
        fi
    else
        exit_code=$?
        log_error "命令失败 (exit=$exit_code): $cmd" "$context" "$phase"

        # 记录完整错误输出
        if [ -s "$temp_output" ]; then
            local error_output=$(cat "$temp_output")
            log_error "错误输出:\n$error_output" "$context" "$phase"
        fi
    fi

    # 将完整输出追加到日志
    if [ -s "$temp_output" ]; then
        local full_output=$(cat "$temp_output")
        _write_log "CMD_OUTPUT" "$full_output" "$context" "$phase"
    fi

    rm -f "$temp_output"
    return $exit_code
}

# 记录环境信息
log_environment() {
    local context="${1:-ENV}"
    local phase="${2:-}"

    log_info "========== 环境信息 ==========" "$context" false "$phase"
    log_info "操作系统: $(uname -s)" "$context" false "$phase"
    log_info "内核版本: $(uname -r)" "$context" false "$phase"
    log_info "架构: $(uname -m)" "$context" false "$phase"

    if command -v python3 >/dev/null 2>&1; then
        local py_version=$(python3 --version 2>&1)
        local py_path=$(which python3)
        log_info "Python: $py_version" "$context" false "$phase"
        log_info "Python 路径: $py_path" "$context" false "$phase"

        # Python 前缀（检测虚拟环境）
        local py_prefix=$(python3 -c "import sys; print(sys.prefix)" 2>/dev/null || echo "未知")
        log_info "Python 前缀: $py_prefix" "$context" false "$phase"
    fi

    if command -v conda >/dev/null 2>&1; then
        local conda_version=$(conda --version 2>&1)
        log_info "Conda: $conda_version" "$context" false "$phase"

        if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
            log_info "Conda 环境: ${CONDA_DEFAULT_ENV:-}" "$context" false "$phase"
        fi
    fi

    if command -v pip >/dev/null 2>&1; then
        local pip_version=$(pip --version 2>&1 | head -1)
        log_info "Pip: $pip_version" "$context" false "$phase"
    fi

    # 环境变量
    log_debug "PATH: $PATH" "$context" "$phase"
    log_debug "PYTHONPATH: ${PYTHONPATH:-<未设置>}" "$context" "$phase"
    log_debug "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-<未设置>}" "$context" "$phase"

    log_info "==============================" "$context" false "$phase"
}

# 显示旋转动画的后台 spinner
_pip_spinner_pid=""
_pip_spinner_running=false

start_spinner() {
    local msg="${1:-安装中}"
    local chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local delay=0.1
    _pip_spinner_running=true

    (
        trap 'exit 0' TERM
        while true; do
            for (( i=0; i<${#chars}; i++ )); do
                printf "\r  ${CYAN}%s${NC} %s..." "${chars:$i:1}" "$msg" >&2
                sleep $delay
            done
        done
    ) &
    _pip_spinner_pid=$!
    disown "$_pip_spinner_pid" 2>/dev/null || true
}

stop_spinner() {
    local success="${1:-true}"
    if [ -n "$_pip_spinner_pid" ]; then
        kill "$_pip_spinner_pid" 2>/dev/null || true
        wait "$_pip_spinner_pid" 2>/dev/null || true
        _pip_spinner_pid=""
    fi
    _pip_spinner_running=false
    printf "\r" >&2  # clear spinner line
}

# 执行 pip 安装命令，带实时进度显示
log_pip_install_with_progress() {
    local context="$1"
    local phase="$2"
    shift 2
    local cmd="$@"

    log_debug "执行命令: $cmd" "$context" "$phase"

    local temp_output
    temp_output=$(mktemp)
    local exit_code=0

    local chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local char_idx=0
    local installed_count=0
    local current_pkg=""
    local last_keepalive=0
    local start_time=$(date +%s)

    echo -e "${DIM}   开始安装，这可能需要几分钟，请耐心等待...${NC}" >&2

    # 使用管道实时读取 pip 输出并更新进度
    {
        eval "$cmd" 2>&1
        echo $? > "${temp_output}.exit"
    } | while IFS= read -r line; do
        echo "$line" >> "$temp_output"

        # 解析 pip 输出，提取正在安装的包名
        if [[ "$line" =~ ^Collecting[[:space:]]+([^[:space:]<>=!]+) ]]; then
            current_pkg="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^Downloading[[:space:]] ]]; then
            # 提取下载的包名
            if [[ "$line" =~ /([^/]+\.whl) ]] || [[ "$line" =~ /([^/]+\.tar\.gz) ]]; then
                current_pkg="${BASH_REMATCH[1]}"
            fi
        elif [[ "$line" =~ Successfully\ installed ]]; then
            # 统计成功安装的包数
            installed_count=$(echo "$line" | grep -oE '[^ ]+' | wc -l)
            ((installed_count = installed_count - 2))  # 减去 "Successfully installed"
        fi

        # 更新 spinner 动画和当前包名
        local spinner_char="${chars:$char_idx:1}"
        char_idx=$(( (char_idx + 1) % ${#chars} ))

        # 保活提示（每30秒）
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        if [ $((current_time - last_keepalive)) -ge 30 ]; then
            printf "\n${DIM}   [%ds] 仍在安装中...${NC}\n" "$elapsed" >&2
            last_keepalive=$current_time
        fi

        if [ -n "$current_pkg" ]; then
            # 截断过长的包名
            local display_pkg="$current_pkg"
            if [ ${#display_pkg} -gt 40 ]; then
                display_pkg="${display_pkg:0:37}..."
            fi
            printf "\r  ${CYAN}%s${NC} 安装依赖包... ${DIM}%s${NC}          " "$spinner_char" "$display_pkg" >&2
        else
            printf "\r  ${CYAN}%s${NC} 安装依赖包...          " "$spinner_char" >&2
        fi
    done

    # 读取退出码
    if [ -f "${temp_output}.exit" ]; then
        exit_code=$(cat "${temp_output}.exit")
        rm -f "${temp_output}.exit"
    fi

    # 清除进度行
    printf "\r                                                              \r" >&2

    if [ "$exit_code" = "0" ]; then
        log_debug "命令成功 (exit=$exit_code): $cmd" "$context" "$phase"
        if [ -s "$temp_output" ]; then
            local output_preview
            output_preview=$(head -10 "$temp_output")
            log_debug "命令输出预览:\n$output_preview" "$context" "$phase"
        fi
    else
        log_error "命令失败 (exit=$exit_code): $cmd" "$context" "$phase"
        if [ -s "$temp_output" ]; then
            local error_output
            error_output=$(cat "$temp_output")
            log_error "错误输出:\n$error_output" "$context" "$phase"
        fi
    fi

    if [ -s "$temp_output" ]; then
        local full_output
        full_output=$(cat "$temp_output")
        _write_log "CMD_OUTPUT" "$full_output" "$context" "$phase"
    fi

    rm -f "$temp_output"
    return $exit_code
}

# 执行 pip 安装命令，显示详细实时输出（用于大型依赖安装）
log_pip_install_with_verbose_progress() {
    local context="$1"
    local phase="$2"
    shift 2
    local cmd="$@"

    log_debug "执行命令（详细输出）: $cmd" "$context" "$phase"

    local temp_output
    temp_output=$(mktemp)
    local exit_code=0

    local start_time=$(date +%s)
    local last_update=0
    local current_pkg=""
    local line_count=0

    echo -e "${DIM}   开始安装，显示详细进度...${NC}" >&2
    echo "" >&2

    # 实时输出 pip 的详细信息
    {
        eval "$cmd" 2>&1
        echo $? > "${temp_output}.exit"
    } | while IFS= read -r line; do
        echo "$line" >> "$temp_output"
        line_count=$((line_count + 1))

        # 显示关键信息行
        if [[ "$line" =~ ^Collecting[[:space:]]+([^[:space:]<>=!]+) ]] ||
           [[ "$line" =~ ^Downloading[[:space:]] ]] ||
           [[ "$line" =~ ^Installing[[:space:]] ]] ||
           [[ "$line" =~ ^Building[[:space:]] ]] ||
           [[ "$line" =~ ^Running[[:space:]]setup\.py ]] ||
           [[ "$line" =~ ^Successfully[[:space:]]installed ]] ||
           [[ "$line" =~ ^Requirement[[:space:]]already[[:space:]]satisfied ]]; then
            # 提取包名用于高亮显示
            if [[ "$line" =~ ^Collecting[[:space:]]+([^[:space:]<>=!]+) ]]; then
                current_pkg="${BASH_REMATCH[1]}"
                echo -e "  ${CYAN}→${NC} ${GREEN}正在收集:${NC} ${BOLD}$current_pkg${NC}" >&2
            elif [[ "$line" =~ ^Downloading[[:space:]].*\.whl ]] || [[ "$line" =~ ^Downloading[[:space:]].*\.tar\.gz ]]; then
                echo -e "  ${DIM}  ⬇ 下载中...${NC}" >&2
            elif [[ "$line" =~ ^Building[[:space:]]wheel ]] || [[ "$line" =~ ^Running[[:space:]]setup\.py ]]; then
                echo -e "  ${YELLOW}  🔨 编译中...${NC} ${DIM}(可能需要几分钟)${NC}" >&2
            elif [[ "$line" =~ ^Successfully[[:space:]]installed ]]; then
                echo -e "  ${GREEN}✓${NC} 安装完成: ${line#Successfully installed }" >&2
            elif [[ "$line" =~ ^Requirement[[:space:]]already[[:space:]]satisfied ]]; then
                # 跳过已满足的依赖（减少输出噪音）
                :
            fi
        fi

        # 时间戳提示（每60秒）
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        if [ $((current_time - last_update)) -ge 60 ]; then
            echo -e "${DIM}   [已运行 ${elapsed}s，处理了 ${line_count} 行输出]${NC}" >&2
            last_update=$current_time
        fi
    done

    # 读取退出码
    if [ -f "${temp_output}.exit" ]; then
        exit_code=$(cat "${temp_output}.exit")
        rm -f "${temp_output}.exit"
    fi

    echo "" >&2

    if [ "$exit_code" = "0" ]; then
        log_debug "命令成功 (exit=$exit_code): $cmd" "$context" "$phase"
    else
        log_error "命令失败 (exit=$exit_code): $cmd" "$context" "$phase"
        if [ -s "$temp_output" ]; then
            echo -e "${RED}错误输出:${NC}" >&2
            tail -20 "$temp_output" >&2
        fi
    fi

    if [ -s "$temp_output" ]; then
        local full_output
        full_output=$(cat "$temp_output")
        _write_log "CMD_OUTPUT" "$full_output" "$context" "$phase"
    fi

    rm -f "$temp_output"
    return $exit_code
}

# 记录 pip 包信息
log_pip_package_info() {
    local package_name="$1"
    local context="${2:-PIP}"
    local phase="${3:-}"

    if command -v pip >/dev/null 2>&1; then
        local pkg_info=$(pip show "$package_name" 2>/dev/null)
        if [ -n "$pkg_info" ]; then
            log_debug "包信息 $package_name:\n$pkg_info" "$context" "$phase"
        else
            log_debug "包 $package_name 未安装" "$context" "$phase"
        fi
    fi
}

# 记录 Python 导入测试
log_python_import_test() {
    local module_name="$1"
    local context="${2:-IMPORT}"
    local phase="${3:-}"

    log_debug "测试导入: $module_name" "$context" "$phase"

    if python3 -c "import $module_name" 2>/dev/null; then
        log_debug "导入成功: $module_name" "$context" "$phase"

        # 尝试获取模块路径
        local module_path=$(python3 -c "import $module_name; print($module_name.__file__ if hasattr($module_name, '__file__') else 'builtin')" 2>/dev/null || echo "未知")
        log_debug "模块路径: $module_path" "$context" "$phase"

        return 0
    else
        local error_msg=$(python3 -c "import $module_name" 2>&1 || true)
        log_debug "导入失败: $module_name\n错误: $error_msg" "$context" "$phase"
        return 1
    fi
}

# 记录阶段开始
log_phase_start() {
    local phase_name="$1"
    local context="${2:-PHASE}"

    log_info "========================================" "$context" false "$phase_name"
    log_info "阶段开始: $phase_name" "$context" true "$phase_name"
    log_info "========================================" "$context" false "$phase_name"
}

# 记录阶段结束
log_phase_end() {
    local phase_name="$1"
    local status="${2:-true}"
    local context="${3:-PHASE}"

    # 支持多种状态表示：
    # - "true" / "success" → 成功
    # - "false" / "failure" → 失败
    # - "partial_success" → 部分成功
    # - "skipped" → 跳过
    case "$status" in
        "true"|"success")
            log_info "阶段完成: $phase_name ✓" "$context" true "$phase_name"
            ;;
        "partial_success")
            log_warn "阶段部分完成: $phase_name ⚠" "$context" true "$phase_name"
            ;;
        "skipped")
            log_info "阶段跳过: $phase_name ⊘" "$context" true "$phase_name"
            ;;
        "false"|"failure"|*)
            log_error "阶段失败: $phase_name ✗" "$context" true "$phase_name"
            ;;
    esac
    log_info "========================================" "$context" false "$phase_name"
}

# 增强的进度可视化 - 带颜色编码和ETA的阶段记录
# 全局变量用于跟踪安装进度
declare -A PHASE_START_TIMES
declare -A PHASE_COLORS=(
    ["环境信息收集"]="$BLUE"
    ["本地依赖包安装"]="$GREEN"
    ["外部依赖安装"]="$YELLOW"
    ["Git钩子安装"]="$PURPLE"
    ["环境配置"]="$CYAN"
)

# 开始带进度可视化的阶段
log_phase_start_enhanced() {
    local phase_name="$1"
    local context="${2:-PHASE}"
    local estimated_time="${3:-}"  # 预估时间（秒），可选

    # 记录开始时间
    PHASE_START_TIMES["$phase_name"]=$(date +%s)

    # 获取阶段颜色
    local phase_color="${PHASE_COLORS[$phase_name]:-$BLUE}"

    echo -e "${phase_color}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${phase_color}  🚀 $phase_name${NC}"

    if [ -n "$estimated_time" ]; then
        local eta_display=""
        if [ "$estimated_time" -lt 60 ]; then
            eta_display="${estimated_time}s"
        elif [ "$estimated_time" -lt 3600 ]; then
            eta_display="$((estimated_time / 60))m $((estimated_time % 60))s"
        else
            eta_display="$((estimated_time / 3600))h $(((estimated_time % 3600) / 60))m"
        fi
        echo -e "${phase_color}  ⏱️  预估时间: ${eta_display}${NC}"
    fi

    echo -e "${phase_color}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # 记录到日志
    log_info "阶段开始: $phase_name" "$context" false "$phase_name"
}

# 结束带进度可视化的阶段
log_phase_end_enhanced() {
    local phase_name="$1"
    local status="${2:-true}"
    local context="${3:-PHASE}"

    # 计算实际耗时
    local start_time="${PHASE_START_TIMES[$phase_name]}"
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # 获取阶段颜色
    local phase_color="${PHASE_COLORS[$phase_name]:-$BLUE}"

    echo -e "${phase_color}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    case "$status" in
        "true"|"success")
            echo -e "${BOLD}${phase_color}  ✅ $phase_name 完成${NC}"
            echo -e "${phase_color}  ⏱️  耗时: ${duration}s${NC}"
            log_info "阶段完成: $phase_name ✓ (耗时: ${duration}s)" "$context" true "$phase_name"
            ;;
        "partial_success")
            echo -e "${BOLD}${YELLOW}  ⚠️  $phase_name 部分完成${NC}"
            echo -e "${YELLOW}  ⏱️  耗时: ${duration}s${NC}"
            log_warn "阶段部分完成: $phase_name ⚠ (耗时: ${duration}s)" "$context" true "$phase_name"
            ;;
        "skipped")
            echo -e "${BOLD}${GRAY}  ⊘ $phase_name 跳过${NC}"
            log_info "阶段跳过: $phase_name ⊘" "$context" true "$phase_name"
            ;;
        "false"|"failure"|*)
            echo -e "${BOLD}${RED}  ❌ $phase_name 失败${NC}"
            echo -e "${RED}  ⏱️  耗时: ${duration}s${NC}"
            log_error "阶段失败: $phase_name ✗ (耗时: ${duration}s)" "$context" true "$phase_name"
            ;;
    esac

    echo -e "${phase_color}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 清理开始时间记录
    unset "PHASE_START_TIMES[$phase_name]"
}

# 导出函数
export -f log_debug log_info log_warn log_error log_command
export -f log_environment log_pip_package_info log_python_import_test
export -f log_phase_start log_phase_end
export -f log_phase_start_enhanced log_phase_end_enhanced
