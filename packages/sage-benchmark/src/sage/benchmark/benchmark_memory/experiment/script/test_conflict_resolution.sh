#!/bin/bash
# Quick test for Conflict Resolution Pipeline
# Run the first sample with progressive testing

set -e

# Get paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../config/conflict_resolution_pipeline.yaml"

echo "========================================================================"
echo "Conflict Resolution Pipeline - Quick Test"
echo "========================================================================"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Test Sample:  factconsolidation_mh_6k"
echo ""

cd "$PROJECT_ROOT"

# Run the first sample
python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "factconsolidation_mh_6k"

echo ""
echo "========================================================================"
echo "Test Complete!"
echo "========================================================================"
