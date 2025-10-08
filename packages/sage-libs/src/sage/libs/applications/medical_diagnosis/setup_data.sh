#!/bin/bash
# 医疗诊断数据集自动下载和准备脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA_DIR="$SCRIPT_DIR/data/processed"

echo "=========================================="
echo "医疗诊断数据集自动设置"
echo "=========================================="

# 检查是否已经存在处理好的数据
if [ -d "$DATA_DIR" ] && [ -f "$DATA_DIR/train_index.json" ]; then
    echo "✓ 数据集已存在: $DATA_DIR"
    echo ""
    
    # 显示数据集统计
    if [ -f "$DATA_DIR/stats.json" ]; then
        echo "📊 数据集统计:"
        python3 -c "
import json
with open('$DATA_DIR/stats.json', 'r') as f:
    stats = json.load(f)
    print(f\"  总样本数: {stats['total_samples']}\")
    print(f\"  训练集: {stats['train_samples']}\")
    print(f\"  测试集: {stats['test_samples']}\")
    print(f\"  疾病类型: {len(stats['disease_distribution'])}\")
"
    fi
    
    echo ""
    echo "如需重新下载，请删除 data/ 目录后重新运行此脚本"
    exit 0
fi

echo "📥 开始下载和准备数据集..."
echo ""

# 1. 安装必要的依赖
echo "1️⃣  检查Python依赖..."
pip install -q huggingface_hub datasets pillow scikit-learn || {
    echo "❌ 依赖安装失败"
    exit 1
}
echo "   ✓ 依赖已安装"

# 2. 下载数据集
echo ""
echo "2️⃣  下载腰椎MRI数据集..."
python3 "$PROJECT_ROOT/scripts/download_lumbar_dataset.py" || {
    echo "❌ 数据集下载失败"
    exit 1
}
echo "   ✓ 数据集下载完成"

# 3. 预处理数据
echo ""
echo "3️⃣  预处理数据集..."
python3 "$SCRIPT_DIR/scripts/prepare_data.py" || {
    echo "❌ 数据预处理失败"
    exit 1
}
echo "   ✓ 数据预处理完成"

# 4. 验证数据
echo ""
echo "4️⃣  验证数据集..."
if [ -f "$DATA_DIR/train_index.json" ] && [ -f "$DATA_DIR/test_index.json" ]; then
    echo "   ✓ 数据集验证成功"
    
    # 显示统计信息
    python3 -c "
import json
with open('$DATA_DIR/stats.json', 'r') as f:
    stats = json.load(f)
    print('')
    print('📊 数据集准备完成!')
    print('=' * 50)
    print(f\"总样本数: {stats['total_samples']}\")
    print(f\"训练集: {stats['train_samples']}\")
    print(f\"测试集: {stats['test_samples']}\")
    print(f\"疾病类型: {len(stats['disease_distribution'])}\")
    print('=' * 50)
"
else
    echo "   ❌ 数据集验证失败"
    exit 1
fi

echo ""
echo "✅ 数据集设置完成！"
echo ""
echo "可以开始使用:"
echo "  python examples/medical_diagnosis/test_diagnosis.py --mode single"
echo "  python examples/medical_diagnosis/run_diagnosis.py --interactive"
echo ""
