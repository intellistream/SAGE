#!/bin/bash
# 停止 Embedding 服务器
# 使用方法: ./stop_embedding_server.sh [port]

set -e

# 默认端口
PORT="${1:-8090}"

echo "=========================================="
echo "Stopping Embedding Server on port ${PORT}"
echo "=========================================="

# 查找占用指定端口的进程
PID=$(lsof -ti:${PORT} 2>/dev/null || echo "")

if [ -z "$PID" ]; then
    echo "No process found on port ${PORT}"
    exit 0
fi

echo "Found process(es): ${PID}"

# 尝试优雅关闭 (SIGTERM)
echo "Sending SIGTERM signal..."
kill -15 ${PID} 2>/dev/null || true

# 等待进程结束
sleep 2

# 检查进程是否还在运行
if ps -p ${PID} > /dev/null 2>&1; then
    echo "Process still running, forcing shutdown (SIGKILL)..."
    kill -9 ${PID} 2>/dev/null || true
    sleep 1
fi

# 再次检查
if lsof -ti:${PORT} > /dev/null 2>&1; then
    echo "Warning: Port ${PORT} is still in use"
    exit 1
else
    echo "Server stopped successfully"
fi

echo "=========================================="
