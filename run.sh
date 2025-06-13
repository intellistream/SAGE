#!/bin/bash
# 设置工作目录
cd /workspace
echo "清理之前的Ray进程..."
ray stop --force 2>/dev/null || true
pkill -f ray 2>/dev/null || true
sleep 2

echo "启动新的Ray集群..."
ray start --head --port=6379 --dashboard-host=0.0.0.0 --dashboard-port=8265 &
sleep 5

echo "运行应用程序..."
# 将workspace添加到Python路径
export PYTHONPATH=/workspace:$PYTHONPATH
python ./app/datastream_rag_pipeline.py