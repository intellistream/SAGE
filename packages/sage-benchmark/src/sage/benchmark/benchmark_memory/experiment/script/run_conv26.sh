#!/bin/bash
# 运行 Locomo 长轮对话记忆实验 - conv-26 任务
# 使用方法: bash script/run_conv26.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录 (从 script/ 向上 7 层到 SAGE/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../../../.." && pwd)"
# Python 脚本的相对路径
PYTHON_SCRIPT="$SCRIPT_DIR/../memory_test_pipeline.py"
# 配置文件路径
CONFIG_FILE="$SCRIPT_DIR/../config/locomo_short_term_memory_pipeline.yaml"

echo "========================================================================"
echo "Locomo 长轮对话记忆实验 - conv-26"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $PYTHON_SCRIPT"
echo "配置文件: $CONFIG_FILE"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 运行实验
python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id conv-26

echo ""
echo "========================================================================"
echo "✅ 实验完成"
echo "========================================================================"
