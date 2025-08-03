#!/bin/bash
# SAGE Extensions 完整一键安装脚本
# 包含构建、安装、测试的完整流程

set -e

echo "=========================================="
echo "SAGE Extensions 完整一键安装脚本"
echo "=========================================="

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# 检查是否在正确的目录
if [ ! -f "setup.py" ] || [ ! -f "pyproject.toml" ]; then
    print_error "请在 sage-extensions 根目录下运行此脚本"
    exit 1
fi

print_status "在正确的目录中: $(pwd)"

# 显示环境信息
echo -e "\n=== 环境信息 ==="
print_info "Python 版本: $(python --version)"
print_info "Pip 版本: $(pip --version)"
print_info "工作目录: $(pwd)"

# 步骤 1: 构建 C++ 扩展
echo -e "\n=== 步骤 1: 构建 C++ 扩展 ==="
echo "开始构建 SAGE DB C++ 扩展..."
if python scripts/build.py; then
    print_status "C++ 扩展构建成功"
else
    print_error "C++ 扩展构建失败"
    exit 1
fi

# 步骤 2: 安装 Python 包
echo -e "\n=== 步骤 2: 安装 Python 包 ==="
echo "开始安装 SAGE Extensions Python 包..."
if pip install -e .; then
    print_status "Python 包安装成功"
else
    print_error "Python 包安装失败"
    exit 1
fi

# 步骤 3: 运行功能测试
echo -e "\n=== 步骤 3: 运行功能测试 ==="
echo "开始运行完整功能测试..."
if python scripts/test_complete.py; then
    print_status "功能测试通过"
else
    print_error "功能测试失败"
    exit 1
fi

# 步骤 4: 最终验证
echo -e "\n=== 步骤 4: 最终验证 ==="
echo "验证安装的 SAGE Extensions..."

python -c "
import sys
from sage.extensions.sage_db import SageDB, IndexType, DistanceMetric

print('=== 安装验证 ===')
print(f'Python 版本: {sys.version}')

# 创建数据库
db = SageDB(dimension=128, index_type=IndexType.FLAT, metric=DistanceMetric.L2)
print(f'✓ 数据库创建成功')
print(f'  - 维度: {db.dimension()}')
print(f'  - 索引类型: {db.index_type()}')

# 添加一些测试数据
vectors = [[0.1] * 128, [0.2] * 128, [0.3] * 128]
metadata = [{'type': 'test', 'id': str(i)} for i in range(3)]

ids = db.add_batch(vectors, metadata)
print(f'✓ 批量添加成功: {len(ids)} 个向量')

# 构建索引
db.build_index()
print('✓ 索引构建成功')

# 搜索测试
query = [0.15] * 128
results = db.search(query, k=2)
print(f'✓ 搜索成功: 找到 {len(results)} 个结果')

print('✓ 所有验证测试通过！')
"

if [ $? -eq 0 ]; then
    print_status "最终验证成功"
else
    print_error "最终验证失败"
    exit 1
fi

# 成功信息
echo -e "\n=========================================="
echo -e "${GREEN}🎉 SAGE Extensions 安装完成！${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}使用方法:${NC}"
echo ""
echo "    from sage.extensions.sage_db import SageDB"
echo "    db = SageDB(dimension=128)"
echo "    db.add([0.1] * 128, {'type': 'example'})"
echo "    db.build_index()"
echo "    results = db.search([0.1] * 128, k=5)"
echo ""
echo -e "${BLUE}更多信息:${NC}"
echo "  📁 测试脚本: scripts/test_complete.py"
echo "  📁 构建脚本: scripts/build.py"
echo "  📚 文档: README.md"
echo ""
echo -e "${GREEN}安装成功！开始使用 SAGE Extensions 吧！${NC}"
