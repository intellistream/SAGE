#!/bin/bash
#
# 测试 faiss_HNSW 算法在 SIFT 数据集上的运行
#
# 使用方法：
#   cd benchmark_anns
#   bash tests/test_faiss_sift.sh
#

set -e

echo "=================================="
echo "测试: faiss_HNSW + SIFT"
echo "=================================="

# 运行测试
python run_benchmark.py \
    --algorithm faiss_HNSW \
    --dataset sift \
    --runbook runbooks/test_simple.yaml \
    --k 10 \
    --output test_output

echo ""
echo "✓ 测试完成！"
echo "查看结果: ls -lh test_output/"
