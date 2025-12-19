#!/bin/bash
# 运行 TiM Locomo PreRetrieval 实验 - expand
# 使用方法: bash script/query_formulation_strategy/run_tim_locomo_expand.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录 (从 script/query_formulation_strategy/ 向上 8 层到 SAGE/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../../../../.." && pwd)"
# Python 脚本的相对路径
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
# 配置文件路径
CONFIG_FILE="$SCRIPT_DIR/../../config/query_formulation_strategy/TiM_locomo_expand_pre_retrieval_pipeline.yaml"

# 定义所有任务 ID
TASK_IDS=(
  "conv-26"
#   "conv-30"
#   "conv-41"
#   "conv-42"
#   "conv-43"
#   "conv-44"
#   "conv-47"
#   "conv-48"
#   "conv-49"
#   "conv-50"
)

echo "========================================================================"
echo "TiM Locomo PreRetrieval 实验 - expand"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $PYTHON_SCRIPT"
echo "配置文件: $CONFIG_FILE"
echo "总任务数: ${#TASK_IDS[@]}"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 依次运行所有任务
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))

  echo "--------------------------------------------------------------------"
  echo "🚀 开始运行任务 [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "--------------------------------------------------------------------"

  python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID"

  if [ $? -eq 0 ]; then
    echo "✅ 任务 $TASK_ID 完成"
  else
    echo "❌ 任务 $TASK_ID 失败"
    exit 1
  fi

  echo ""
done

echo "========================================================================"
echo "🎉 所有任务执行完毕 - TiM-expand"
echo "========================================================================"
