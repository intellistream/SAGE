#!/bin/bash
# set -e

echo "=========== 清理SAGE环境 ==========="

# 清理Ray
ray stop --force 2>/dev/null || true
pkill -f ray 2>/dev/null || true
sleep 2

# 清理TCP端口
function kill_port() {
    PORT=$1
    PID=$(lsof -ti tcp:$PORT)
    if [ ! -z "$PID" ]; then
        echo "杀掉占用端口 $PORT 的进程 $PID"
        kill -9 $PID
    fi
}

kill_port 9999
kill_port 10000
kill_port 10001

# 可选：全端口暴力清理
# for PID in $(lsof -iTCP -sTCP:LISTEN -t); do
#     echo "杀掉PID $PID"
#     kill -9 $PID
# done

# 清理日志
rm -rf /tmp/ray/session_*/logs/*
# rm -rf ./logs/*

echo "=========== 启动SAGE任务 ==========="

# 添加工作目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
# python ./app/example/external_memory_ingestion_pipeline.py
# python ./app/local_pipeline.py
# python ./app/pipeline_test.py
# python ./app/example/multiple_pipeline.py
# python ./app/example/qa_dense_retrieval.py
# python ./app/example/qa_dense_retrieval_ray.py
# python ./sage/tests/runtime/qa_dense_retrieval_mixed.py
python ./app/example/qa_dense_retrieval_mixed.py

# python ./app/example/qa_pipeline_flink.py

