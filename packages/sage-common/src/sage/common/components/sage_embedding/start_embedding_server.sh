#!/bin/bash
# 启动 BAAI/bge-m3 Embedding 服务器
# 使用方法: ./start_embedding_server.sh [port] [gpu_id]
# 示例: ./start_embedding_server.sh 8090 0  # 使用 GPU 0
#       ./start_embedding_server.sh 8090 1  # 使用 GPU 1
#       ./start_embedding_server.sh 8090    # 自动选择（默认）

set -e

# 默认参数
MODEL="BAAI/bge-m3"
PORT="${1:-8090}"
GPU_ID="${2:-}"
DEVICE="auto"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMBEDDING_SERVER="${SCRIPT_DIR}/embedding_server.py"

# 检查脚本是否存在
if [ ! -f "${EMBEDDING_SERVER}" ]; then
    echo "Error: embedding_server.py not found at ${EMBEDDING_SERVER}"
    echo "Current directory: ${SCRIPT_DIR}"
    exit 1
fi

# 检查依赖
echo "Checking dependencies..."
python3 -c "import fastapi, uvicorn, transformers, torch" 2>/dev/null || {
    echo "Missing dependencies. Installing..."
    pip install fastapi uvicorn transformers torch -q
}

echo "=========================================="
echo "Starting Embedding Server"
echo "=========================================="
echo "Model: ${MODEL}"
echo "Port: ${PORT}"
if [ -n "${GPU_ID}" ]; then
    echo "GPU: ${GPU_ID}"
    export CUDA_VISIBLE_DEVICES="${GPU_ID}"
else
    echo "GPU: auto (all available)"
fi
echo "Device: ${DEVICE}"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# 启动服务器
python3 "${EMBEDDING_SERVER}" \
    --model "${MODEL}" \
    --port "${PORT}" \
    --device "${DEVICE}" \
    --workers 1
