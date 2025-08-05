#!/bin/bash

# 💡 提示语
echo "🌱 请输入你想创建的 Conda 环境名（默认：lumi-env）："
read ENV_NAME

# 若用户没输入就用默认名
if [ -z "$ENV_NAME" ]; then
  ENV_NAME="lumi-env"
fi

echo "📦 创建 Python 3.11 的 Conda 环境：$ENV_NAME"

# 创建环境
conda create -y -n "$ENV_NAME" python=3.11

# 初始化 shell（确保 conda activate 可用）
eval "$(conda shell.bash hook)"
# 激活环境
conda activate "$ENV_NAME"

# 打印成功提示
echo "✅ 已成功创建并激活环境：$ENV_NAME"
echo "📍 当前 Python 版本：$(python --version)"
