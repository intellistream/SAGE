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
        echo "停止了占用端口 $PORT 的进程 $PID"
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
export ALIBABA_API_KEY=sk-b21a67cf99d14ead9d1c5bf8c2eb90ef

# python ./app/example/external_memory_ingestion_pipeline.py
# python ./app/local_pipeline.py
# python ./app/pipeline_test.py
# python ./sage_examples/qa_dense_retrieval.py
# python sage_tests/test_api/integrated_test/pipeline_test.py
python sage_frontend/sage_server/main.py --host 0.0.0.0 --port 8080 --log-level debug
python ./sage_examples/qa_recycle_test.py
