#!/bin/bash
# Run Conflict Resolution Fact Memory Test - Batch Mode
# Usage: bash script/run_conflict_resolution.sh

set -e  # Exit on error

# Get absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../config/conflict_resolution_pipeline.yaml"

# Define all task IDs (8 samples in Conflict Resolution dataset)
TASK_IDS=(
  "factconsolidation_mh_6k"
  "factconsolidation_mh_32k"
  "factconsolidation_mh_64k"
  "factconsolidation_mh_262k"
  "factconsolidation_sh_6k"
  "factconsolidation_sh_32k"
  "factconsolidation_sh_64k"
  "factconsolidation_sh_262k"
)

echo "========================================================================"
echo "Conflict Resolution Fact Memory Test - Batch Run"
echo "========================================================================"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Python Script: $PYTHON_SCRIPT"
echo "Config File: $CONFIG_FILE"
echo "Total Tasks: ${#TASK_IDS[@]}"
echo ""

# Change to project root directory
cd "$PROJECT_ROOT"

# Run all tasks sequentially
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))

  echo "--------------------------------------------------------------------"
  echo "Running Task [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "--------------------------------------------------------------------"
  echo ""

  # Run experiment
  python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID"

  echo ""
  echo "Task $TASK_ID completed [$TASK_NUM/${#TASK_IDS[@]}]"
  echo ""
done

echo "========================================================================"
echo "All tasks completed! Total: ${#TASK_IDS[@]} tasks"
echo "========================================================================"
