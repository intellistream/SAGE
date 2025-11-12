#!/bin/bash
# 增强的日志记录工具
# 提供结构化、分级的日志记录功能

source "$(dirname "${BASH_SOURCE[0]}")/colors.sh"

# 日志级别
LOG_LEVEL_DEBUG=0
LOG_LEVEL_INFO=1
LOG_LEVEL_WARN=2
LOG_LEVEL_ERROR=3

# 当前日志级别（默认 INFO）
CURRENT_LOG_LEVEL=${SAGE_LOG_LEVEL:-$LOG_LEVEL_INFO}

# 日志文件路径（全局变量，由主安装脚本设置）
SAGE_INSTALL_LOG="${SAGE_INSTALL_LOG:-.sage/logs/install.log}"

# 确保日志目录存在
_ensure_log_dir() {
    local log_dir=$(dirname "$SAGE_INSTALL_LOG")
    mkdir -p "$log_dir" 2>/dev/null || true
}

# 格式化时间戳
_log_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# 写入日志文件（总是写入，不受日志级别影响）
_write_log() {
    local level="$1"
    local message="$2"
    local context="${3:-}"

    _ensure_log_dir

    if [ -n "$context" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [$context] $message" >> "$SAGE_INSTALL_LOG"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$SAGE_INSTALL_LOG"
    fi
}

# DEBUG 级别日志（详细调试信息）
log_debug() {
    local message="$1"
    local context="${2:-}"

    if [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_DEBUG ]; then
        echo -e "${DIM}[DEBUG] $message${NC}" >&2
    fi

    _write_log "DEBUG" "$message" "$context"
}

# INFO 级别日志（一般信息）
log_info() {
    local message="$1"
    local context="${2:-}"
    local show_console="${3:-true}"

    if [ "$show_console" = "true" ] && [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_INFO ]; then
        echo -e "${DIM}[INFO] $message${NC}"
    fi

    _write_log "INFO" "$message" "$context"
}

# WARN 级别日志（警告）
log_warn() {
    local message="$1"
    local context="${2:-}"

    if [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_WARN ]; then
        echo -e "${YELLOW}[WARN] $message${NC}" >&2
    fi

    _write_log "WARN" "$message" "$context"
}

# ERROR 级别日志（错误）
log_error() {
    local message="$1"
    local context="${2:-}"

    if [ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_ERROR ]; then
        echo -e "${RED}[ERROR] $message${NC}" >&2
    fi

    _write_log "ERROR" "$message" "$context"
}

# 记录命令执行（带返回值和输出）
log_command() {
    local context="$1"
    shift
    local cmd="$@"

    log_debug "执行命令: $cmd" "$context"

    # 创建临时文件存储输出
    local temp_output=$(mktemp)
    local exit_code=0

    # 执行命令并捕获输出和返回值
    if eval "$cmd" > "$temp_output" 2>&1; then
        exit_code=0
        log_debug "命令成功 (exit=$exit_code): $cmd" "$context"

        # 如果输出不为空，记录前10行
        if [ -s "$temp_output" ]; then
            local output_preview=$(head -10 "$temp_output")
            log_debug "命令输出预览:\n$output_preview" "$context"
        fi
    else
        exit_code=$?
        log_error "命令失败 (exit=$exit_code): $cmd" "$context"

        # 记录完整错误输出
        if [ -s "$temp_output" ]; then
            local error_output=$(cat "$temp_output")
            log_error "错误输出:\n$error_output" "$context"
        fi
    fi

    # 将完整输出追加到日志
    if [ -s "$temp_output" ]; then
        echo "--- 命令完整输出 START ---" >> "$SAGE_INSTALL_LOG"
        cat "$temp_output" >> "$SAGE_INSTALL_LOG"
        echo "--- 命令完整输出 END ---" >> "$SAGE_INSTALL_LOG"
    fi

    rm -f "$temp_output"
    return $exit_code
}

# 记录环境信息
log_environment() {
    local context="${1:-ENV}"

    log_info "========== 环境信息 ==========" "$context" false
    log_info "操作系统: $(uname -s)" "$context" false
    log_info "内核版本: $(uname -r)" "$context" false
    log_info "架构: $(uname -m)" "$context" false

    if command -v python3 >/dev/null 2>&1; then
        local py_version=$(python3 --version 2>&1)
        local py_path=$(which python3)
        log_info "Python: $py_version" "$context" false
        log_info "Python 路径: $py_path" "$context" false

        # Python 前缀（检测虚拟环境）
        local py_prefix=$(python3 -c "import sys; print(sys.prefix)" 2>/dev/null || echo "未知")
        log_info "Python 前缀: $py_prefix" "$context" false
    fi

    if command -v conda >/dev/null 2>&1; then
        local conda_version=$(conda --version 2>&1)
        log_info "Conda: $conda_version" "$context" false

        if [ -n "$CONDA_DEFAULT_ENV" ]; then
            log_info "Conda 环境: $CONDA_DEFAULT_ENV" "$context" false
        fi
    fi

    if command -v pip >/dev/null 2>&1; then
        local pip_version=$(pip --version 2>&1 | head -1)
        log_info "Pip: $pip_version" "$context" false
    fi

    # 环境变量
    log_debug "PATH: $PATH" "$context"
    log_debug "PYTHONPATH: ${PYTHONPATH:-<未设置>}" "$context"
    log_debug "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-<未设置>}" "$context"

    log_info "==============================" "$context" false
}

# 记录 pip 包信息
log_pip_package_info() {
    local package_name="$1"
    local context="${2:-PIP}"

    if command -v pip >/dev/null 2>&1; then
        local pkg_info=$(pip show "$package_name" 2>/dev/null)
        if [ -n "$pkg_info" ]; then
            log_debug "包信息 $package_name:\n$pkg_info" "$context"
        else
            log_debug "包 $package_name 未安装" "$context"
        fi
    fi
}

# 记录 Python 导入测试
log_python_import_test() {
    local module_name="$1"
    local context="${2:-IMPORT}"

    log_debug "测试导入: $module_name" "$context"

    if python3 -c "import $module_name" 2>/dev/null; then
        log_debug "导入成功: $module_name" "$context"

        # 尝试获取模块路径
        local module_path=$(python3 -c "import $module_name; print($module_name.__file__ if hasattr($module_name, '__file__') else 'builtin')" 2>/dev/null || echo "未知")
        log_debug "模块路径: $module_path" "$context"

        return 0
    else
        local error_msg=$(python3 -c "import $module_name" 2>&1 || true)
        log_debug "导入失败: $module_name\n错误: $error_msg" "$context"
        return 1
    fi
}

# 记录阶段开始
log_phase_start() {
    local phase_name="$1"
    local context="${2:-PHASE}"

    log_info "========================================" "$context" false
    log_info "阶段开始: $phase_name" "$context"
    log_info "========================================" "$context" false
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
            log_info "阶段完成: $phase_name ✓" "$context"
            ;;
        "partial_success")
            log_warn "阶段部分完成: $phase_name ⚠" "$context"
            ;;
        "skipped")
            log_info "阶段跳过: $phase_name ⊘" "$context"
            ;;
        "false"|"failure"|*)
            log_error "阶段失败: $phase_name ✗" "$context"
            ;;
    esac
    log_info "========================================" "$context" false
}

# 导出函数
export -f log_debug log_info log_warn log_error log_command
export -f log_environment log_pip_package_info log_python_import_test
export -f log_phase_start log_phase_end
