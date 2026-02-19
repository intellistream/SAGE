#!/bin/bash
# 升级 Worker 节点的 isage-flownet 版本到与 Head 节点一致
# 替代原 upgrade_worker_ray.sh (legacy runtime 已迁移至 isage-flownet)

set -e

# 配置
WORKERS=("sage@sage2:22" "sage@sage3:22" "sage@sage4:22")
TARGET_FLOWNET_VERSION="0.1.0"
CONDA_ENV="sage"

echo "======================================"
echo "升级 Worker 节点 isage-flownet 版本"
echo "目标版本: $TARGET_FLOWNET_VERSION"
echo "======================================"

for worker in "${WORKERS[@]}"; do
    IFS=':' read -r user_host port <<< "$worker"
    IFS='@' read -r user host <<< "$user_host"

    echo ""
    echo "处理节点: $host"
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

# 检查当前 isage-flownet 版本
CURRENT_VERSION=\$(python -c "import importlib.metadata; print(importlib.metadata.version('isage-flownet'))" 2>/dev/null || echo "未安装")
echo "[INFO] 当前 isage-flownet 版本: \$CURRENT_VERSION"

# 升级 isage-flownet
if [ "\$CURRENT_VERSION" != "$TARGET_FLOWNET_VERSION" ]; then
    echo "[INFO] 升级 isage-flownet 到 $TARGET_FLOWNET_VERSION..."
    pip install --upgrade "isage-flownet==$TARGET_FLOWNET_VERSION"

    # 验证安装
    NEW_VERSION=\$(python -c "import importlib.metadata; print(importlib.metadata.version('isage-flownet'))")
    if [ "\$NEW_VERSION" = "$TARGET_FLOWNET_VERSION" ]; then
        echo "✅ isage-flownet 升级成功: \$NEW_VERSION"
    else
        echo "❌ isage-flownet 升级失败: 期望 $TARGET_FLOWNET_VERSION, 实际 \$NEW_VERSION"
        exit 1
    fi
else
    echo "✅ isage-flownet 版本已是最新: \$CURRENT_VERSION"
fi

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
