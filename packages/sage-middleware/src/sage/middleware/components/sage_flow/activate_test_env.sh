#!/bin/bash

# SAGE Flow 测试环境激活脚本
# 使用方法: source activate_test_env.sh

# 激活 conda 环境
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate sage

# 设置环境变量
export SAGE_FLOW_ROOT="/home/xinyan/0904backup/SAGE/packages/sage-middleware/src/sage/middleware/components/sage_flow"
export SAGE_FLOW_BUILD_DIR="$SAGE_FLOW_ROOT/build"
export PYTHONPATH="$SAGE_FLOW_ROOT:$PYTHONPATH"

# 显示环境信息
echo "SAGE Flow 测试环境已激活"
echo "Python: $(python --version)"
echo "环境: $(conda info --envs | grep '*' | awk '{print $1}')"
echo "项目根目录: $SAGE_FLOW_ROOT"

# 设置别名
alias sage-build="cd $SAGE_FLOW_ROOT && ./scripts/build_test.sh"
alias sage-test="cd $SAGE_FLOW_ROOT && python -m pytest tests/"
alias sage-clean="rm -rf $SAGE_FLOW_BUILD_DIR"

echo "可用别名:"
echo "  sage-build  - 构建项目"
echo "  sage-test   - 运行测试"
echo "  sage-clean  - 清理构建"
