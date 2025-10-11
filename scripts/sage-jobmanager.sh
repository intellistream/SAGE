#!/bin/bash

# sage-jobmanager 命令包装器 - 在正确的 conda 环境中执行 jobmanager 命令

# 获取当前脚本的路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 确定 conda 环境
if [[ -n $CONDA_PREFIX ]]; then
    # 如果已经在 conda 环境中，使用当前环境
    CONDA_ENV="$CONDA_PREFIX"
    echo "Using current conda environment: $CONDA_ENV"
else
    # 尝试使用 sage 环境，如果存在的话
    if conda env list | grep -q "sage"; then
        CONDA_ENV="$(conda env list | grep "sage" | awk '{print $2}' | head -n 1)"
        echo "Using detected sage conda environment: $CONDA_ENV"
    else
        echo "Error: Not in a conda environment and no 'sage' environment found."
        echo "Please activate your conda environment first:"
        echo "  conda activate sage"
        exit 1
    fi
fi

# 构建 Python 可执行文件路径
PYTHON_PATH="$CONDA_ENV/bin/python"

if [[ ! -f "$PYTHON_PATH" ]]; then
    echo "Error: Python executable not found at $PYTHON_PATH"
    exit 1
fi

# 执行 jobmanager 命令
$PYTHON_PATH -m sage.cli.commands.jobmanager "$@"

# 获取命令执行状态
exit_code=$?

# 返回相同的退出状态
exit $exit_code
