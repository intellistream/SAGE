#!/bin/bash
# 在 SAGE 中添加 sageRefiner submodule
# 前提：sageRefiner 已经推送到 GitHub

set -e

echo "==================================================================="
echo "在 SAGE 中添加 sageRefiner Submodule"
echo "==================================================================="

cd /home/cyb/SAGE

# 检查是否已经推送到 GitHub
echo ""
echo "检查 sageRefiner 远程仓库..."
if ! git ls-remote https://github.com/intellistream/sageRefiner.git HEAD > /dev/null 2>&1; then
    echo "❌ 错误：sageRefiner 仓库不存在或无法访问"
    echo "请先运行 /tmp/push_sagerefiner.sh 推送代码"
    exit 1
fi

echo "✅ sageRefiner 远程仓库可访问"

# 移除临时复制的目录
echo ""
echo "移除临时 sageRefiner 目录..."
if [ -d "packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner" ]; then
    # 取消暂存
    git reset HEAD packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner 2>/dev/null || true
    # 删除目录
    rm -rf packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner
    echo "✅ 临时目录已删除"
fi

# 正式添加 submodule
echo ""
echo "添加 sageRefiner 为 Git Submodule..."
git submodule add -b main \
    https://github.com/intellistream/sageRefiner.git \
    packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner

echo ""
echo "✅ Submodule 添加成功！"

# 初始化并更新 submodule
echo ""
echo "初始化 submodule..."
git submodule update --init --recursive packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner

echo ""
echo "==================================================================="
echo "✅ sageRefiner Submodule 配置完成"
echo "==================================================================="
echo ""
echo "下一步："
echo "  1. 检查状态：git status"
echo "  2. 提交更改：git add . && git commit -m 'feat: add sageRefiner submodule'"
echo "  3. 推送：git push origin feature/refiner"
