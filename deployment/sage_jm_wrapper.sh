#!/bin/bash
# SAGE JobManager CLI Wrapper Script
# 这个脚本确保CLI工具在正确的环境下运行，解决多用户权限问题

# 获取脚本的实际位置
SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONTROLLER_SCRIPT="$SCRIPT_DIR/jobmanager_controller.py"

# 检查controller脚本是否存在
if [ ! -f "$CONTROLLER_SCRIPT" ]; then
    echo "Error: JobManager controller script not found at $CONTROLLER_SCRIPT" >&2
    exit 1
fi

# 设置Python路径，确保能找到sage模块
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 获取合适的Python命令（支持conda环境）
get_python_command() {
    # 如果在conda环境中，使用当前环境的python
    if [ -n "$CONDA_DEFAULT_ENV" ] && [ "$CONDA_DEFAULT_ENV" != "base" ]; then
        echo "python3"
        return
    fi
    
    # 检查是否有sage conda环境
    if command -v conda >/dev/null 2>&1; then
        if conda info --envs 2>/dev/null | grep -q "sage"; then
            echo "conda run -n sage python3"
            return
        fi
    fi
    
    # 检查mamba环境
    if command -v mamba >/dev/null 2>&1; then
        if mamba info --envs 2>/dev/null | grep -q "sage"; then
            echo "mamba run -n sage python3"
            return
        fi
    fi
    
    # 使用系统python
    echo "python3"
}

# 获取Python命令
PYTHON_CMD=$(get_python_command)

# 执行controller脚本
exec $PYTHON_CMD "$CONTROLLER_SCRIPT" "$@"
