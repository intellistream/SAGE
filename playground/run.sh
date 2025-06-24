#!/bin/bash
# 设置工作目录
cd /workspace

# 将workspace添加到Python路径
export PYTHONPATH=/workspace:$PYTHONPATH
python ./app/datastream_rag_pipeline.py