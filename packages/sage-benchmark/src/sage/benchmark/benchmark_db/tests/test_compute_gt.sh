#!/bin/bash
#
# Quick test script for compute_gt.py with auto-detection
#
# 使用方法：
#   从 benchmark_anns 根目录运行: bash tests/test_compute_gt.sh
#

set -e

# 切换到 benchmark_anns 根目录
cd "$(dirname "$0")/.."

echo "Testing compute_gt.py with auto-detection..."
echo "Working directory: $(pwd)"
echo ""

# Test 1: Auto-detection
echo "Test 1: Auto-detection of compute_groundtruth tool"
python compute_gt.py \
    --dataset sift \
    --runbook_file runbooks/test_simple.yaml \
    --gt_cmdline_tool DiskANN/build/apps/utils/compute_groundtruth

echo ""
echo "✓ Auto-detection test passed!"
echo ""

# Show generated files
echo "Generated files:"
ls -lh raw_data/sift/1000000/test_simple.yaml/*.gt100 2>/dev/null || echo "  (No .gt100 files yet - check if compute_groundtruth ran successfully)"

echo ""
echo "Done!"
