#!/bin/bash
# 设置工作目录
echo "清理之前的Ray进程..."
ray stop --force 2>/dev/null || true
pkill -f ray 2>/dev/null || true
sleep 2

# echo "启动新的Ray集群..."
# ray start --head --port=6379 --dashboard-host=0.0.0.0 --dashboard-port=8265 &
# sleep 5
# 将workspace添加到Python路径

# 获取脚本所在目录（绝对路径）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# 添加脚本所在目录到 PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
python ./app/qa_pipeline.py
# python ./app/local_pipeline.py
# python ./app/pipeline_test.py
