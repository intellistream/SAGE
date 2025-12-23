#!/bin/bash
# Run Conflict Resolution memory experiment - Short Term Memory (STM) batch test
# Usage: bash script/run_conflict_resolution_stm.sh

set -e  # Exit immediately on error

# Get absolute path of script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get project root directory (from script/ up 7 levels to SAGE/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../../../.." && pwd)"
# Python script relative path
PYTHON_SCRIPT="$SCRIPT_DIR/../memory_test_pipeline.py"
# Configuration file path
CONFIG_FILE="$SCRIPT_DIR/../config/conflict_resolution_short_term_memory_pipeline.yaml"

# Define all task IDs
TASK_IDS=(
  "task_all"
)

echo "========================================================================"
echo "Conflict Resolution Memory Experiment - Short Term Memory (STM) Batch Test"
echo "========================================================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo "Python script: $(realpath "$PYTHON_SCRIPT")"
echo "Config file: $(realpath "$CONFIG_FILE")"
echo "Total tasks: ${#TASK_IDS[@]}"
echo ""

# Change to project root directory
cd "$PROJECT_ROOT"

# Run all tasks sequentially
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))

  echo "--------------------------------------------------------------------"
  echo "? Starting task [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "--------------------------------------------------------------------"
  echo ""

  # Run experiment
  python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID"

  echo ""
  echo "? Task $TASK_ID completed [$TASK_NUM/${#TASK_IDS[@]}]"
  echo ""
done

echo "========================================================================"
echo "? All tasks completed! Total: ${#TASK_IDS[@]} tasks"
echo "========================================================================"
