#!/bin/bash
# 日志管理工具：压缩旧日志

# 日志目录

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

LOG_DIR="$1"
if [ -z "$LOG_DIR" ]; then
    echo "Usage: $0 <log_directory>"
    exit 1
fi

# 日志文件模式
LOG_FILE_PATTERN="install.log"

# 检查日志目录是否存在
if [ ! -d "$LOG_DIR" ]; then
    echo "Log directory not found: $LOG_DIR"
    exit 0
fi

# 查找并压缩旧日志
find "$LOG_DIR" -name "${LOG_FILE_PATTERN}.*" -type f -mtime +7 -print0 | while IFS= read -r -d $'\0' log_file; do
    if [[ ! "$log_file" =~ \.gz$ ]]; then
        echo "Compressing old log file: $log_file"
        gzip "$log_file"
    fi
done

# 轮转当前日志文件
CURRENT_LOG_FILE="$LOG_DIR/$LOG_FILE_PATTERN"
if [ -f "$CURRENT_LOG_FILE" ]; then
    # 如果日志文件大于1MB，则轮转
    file_size=$(stat -c%s "$CURRENT_LOG_FILE")
    if [ "$file_size" -gt 1048576 ]; then
        timestamp=$(date +%Y%m%d-%H%M%S)
        mv "$CURRENT_LOG_FILE" "${CURRENT_LOG_FILE}.${timestamp}"
        echo "Rotated log file: ${CURRENT_LOG_FILE}.${timestamp}"
    fi
fi
