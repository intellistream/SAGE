#!/usr/bin/env bash
set -euo pipefail

# Check if vllm is installed in the current conda environment
if ! command -v vllm >/dev/null 2>&1; then
    echo "vllm not found, installing via conda..."
    conda install -y -c conda-forge vllm
fi

# 启动 vllm 本地服务，加载指定模型并使用 API key
vllm serve meta-llama/Llama-2-13b-chat-hf --dtype auto --api-key token-abc123