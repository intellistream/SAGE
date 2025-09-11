#!/usr/bin/env python3
"""
vLLM 本地服务启动脚本
用于启动 vLLM 服务加载指定模型
"""

import os
import subprocess
import sys

def run_command(cmd, check=True, capture_output=False):
    """运行命令并检查返回值"""
    result = subprocess.run(cmd, check=check, capture_output=capture_output)
    return result

# 检查 vllm 是否已安装
if run_command(['command', '-v', 'vllm'], check=False, capture_output=True).returncode != 0:
    print("vllm not found, installing via conda...")
    run_command(['conda', 'install', '-y', '-c', 'conda-forge', 'vllm'])

# 启动 vllm 本地服务
print("启动 vLLM 服务...")
run_command([
    'vllm', 'serve', 'meta-llama/Llama-2-13b-chat-hf',
    '--dtype', 'auto', '--api-key', 'token-abc123'
])