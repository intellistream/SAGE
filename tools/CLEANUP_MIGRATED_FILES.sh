#!/bin/bash
# 清理已迁移到 sage-tools 的文件
# 执行前请确保新功能已测试通过

set -e

echo "🧹 开始清理已迁移的文件..."
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录（tools/）
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$TOOLS_DIR")"

echo "📂 工作目录: $TOOLS_DIR"
echo "📂 项目根目录: $PROJECT_ROOT"
echo ""

# 确认操作
echo -e "${YELLOW}⚠️  警告：此操作将删除以下已迁移的文件：${NC}"
echo ""
echo "1. tools/maintenance/helpers/devnotes_organizer.py"
echo "2. tools/maintenance/helpers/batch_fix_devnotes_metadata.py"
echo "3. tools/maintenance/helpers/update_ruff_ignore.py"
echo "4. tools/tests/ 中已迁移的文件"
echo ""
echo -e "${GREEN}✅ 这些文件已迁移到: packages/sage-tools/${NC}"
echo ""

read -p "确认删除? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}❌ 操作已取消${NC}"
    exit 0
fi

echo ""
echo "🗑️  开始删除..."
echo ""

# 删除已迁移的 Python 维护脚本
DELETED_COUNT=0

delete_file() {
    local file="$1"
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} 删除: $file"
        rm "$file"
        ((DELETED_COUNT++))
    else
        echo -e "${YELLOW}⊘${NC} 文件不存在: $file"
    fi
}

# 删除维护工具脚本
delete_file "$TOOLS_DIR/maintenance/helpers/devnotes_organizer.py"
delete_file "$TOOLS_DIR/maintenance/helpers/batch_fix_devnotes_metadata.py"
delete_file "$TOOLS_DIR/maintenance/helpers/update_ruff_ignore.py"

# 删除 tools/tests 中已迁移的文件
# 注意：保留一些仍在使用的测试文件
TESTS_TO_DELETE=(
    "check_intermediate_results.py"
    "example_strategies.py"
    "run_examples_tests.sh"
    "test_examples.py"
    "test_examples_pytest.py"
)

echo ""
echo "🗑️  删除 tools/tests/ 中已迁移的文件..."

for test_file in "${TESTS_TO_DELETE[@]}"; do
    delete_file "$TOOLS_DIR/tests/$test_file"
done

# 删除 pytest 配置（已在 sage-tools 中）
delete_file "$TOOLS_DIR/tests/pytest.ini"
delete_file "$TOOLS_DIR/tests/conftest.py"

# 删除 __pycache__
if [ -d "$TOOLS_DIR/tests/__pycache__" ]; then
    echo -e "${GREEN}✓${NC} 删除: tools/tests/__pycache__/"
    rm -rf "$TOOLS_DIR/tests/__pycache__"
    ((DELETED_COUNT++))
fi

if [ -d "$TOOLS_DIR/maintenance/helpers/__pycache__" ]; then
    echo -e "${GREEN}✓${NC} 删除: tools/maintenance/helpers/__pycache__/"
    rm -rf "$TOOLS_DIR/maintenance/helpers/__pycache__"
    ((DELETED_COUNT++))
fi

echo ""
echo "=" * 80
echo -e "${GREEN}✅ 清理完成！${NC}"
echo "   删除了 $DELETED_COUNT 个文件/目录"
echo ""
echo "📝 注意事项："
echo "   1. 旧文件已删除，请使用新的 CLI 命令"
echo "   2. 新用法: sage-dev maintenance <command>"
echo "   3. 新用法: sage-dev examples <command>"
echo ""
echo "📚 查看帮助："
echo "   sage-dev maintenance --help"
echo "   sage-dev examples --help"
echo ""
echo "🔄 如需恢复，可以从 Git 历史中恢复"
echo "=" * 80
