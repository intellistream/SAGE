#!/bin/bash
# 升级 Worker 节点的 Ray 版本到与 Head 节点一致

set -e

# 配置
WORKERS=("sage@sage2:22" "sage@sage3:22" "sage@sage4:22")
TARGET_RAY_VERSION="2.52.0"
CONDA_ENV="sage"

echo "======================================"
echo "升级 Worker 节点 Ray 版本"
echo "目标版本: $TARGET_RAY_VERSION"
echo "======================================"

for worker in "${WORKERS[@]}"; do
    IFS=':' read -r user_host port <<< "$worker"
    IFS='@' read -r user host <<< "$user_host"
    
    echo ""
    echo "🔧 处理节点: $host"
    echo "--------------------------------------"
    
    # SSH 执行升级命令
    ssh -o StrictHostKeyChecking=no -p "$port" "${user}@${host}" << EOF
set -e

# 激活 conda 环境
if [ -f /opt/conda/etc/profile.d/conda.sh ]; then
    source /opt/conda/etc/profile.d/conda.sh
    conda activate $CONDA_ENV
elif [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate $CONDA_ENV
else
    echo "❌ 找不到 conda"
    exit 1
fi

echo "[INFO] 当前环境: \$(conda info --envs | grep '*' | awk '{print \$1}')"

# 检查当前 Ray 版本
CURRENT_VERSION=\$(python -c "import ray; print(ray.__version__)" 2>/dev/null || echo "未安装")
echo "[INFO] 当前 Ray 版本: \$CURRENT_VERSION"

# 停止现有 Ray 进程
echo "[INFO] 停止现有 Ray 进程..."
ray stop 2>/dev/null || true
pkill -f "ray.*start" 2>/dev/null || true
pkill -f "raylet" 2>/dev/null || true
sleep 2

# 升级 Ray
if [ "\$CURRENT_VERSION" != "$TARGET_RAY_VERSION" ]; then
    echo "[INFO] 升级 Ray 到 $TARGET_RAY_VERSION..."
    pip install --upgrade "ray[default]==$TARGET_RAY_VERSION"
    
    # 验证安装
    NEW_VERSION=\$(python -c "import ray; print(ray.__version__)")
    if [ "\$NEW_VERSION" = "$TARGET_RAY_VERSION" ]; then
        echo "✅ Ray 升级成功: \$NEW_VERSION"
    else
        echo "❌ Ray 升级失败: 期望 $TARGET_RAY_VERSION, 实际 \$NEW_VERSION"
        exit 1
    fi
else
    echo "✅ Ray 版本已是最新: \$CURRENT_VERSION"
fi

# 清理旧的临时文件
echo "[INFO] 清理 Ray 临时文件..."
rm -rf /tmp/ray_* 2>/dev/null || true

EOF
    
    if [ $? -eq 0 ]; then
        echo "✅ 节点 $host 升级成功"
    else
        echo "❌ 节点 $host 升级失败"
    fi
done

echo ""
echo "======================================"
echo "✅ 所有 Worker 节点处理完毕"
echo "======================================"
echo ""
echo "现在可以运行: sage cluster start"
