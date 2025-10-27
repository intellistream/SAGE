#!/bin/bash
# 安全清理：先创建备份，再删除已迁移的文件
# 备份位置：tools/backup_$(date +%Y%m%d_%H%M%S)/

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取目录
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$TOOLS_DIR/backup_$(date +%Y%m%d_%H%M%S)"

echo "🧹 安全清理已迁移文件"
echo "=" * 80
echo ""

# 创建备份目录
mkdir -p "$BACKUP_DIR"
echo -e "${BLUE}📦 备份目录: $BACKUP_DIR${NC}"
echo ""

# 要删除的文件列表
FILES_TO_DELETE=(
    "maintenance/helpers/devnotes_organizer.py"
    "maintenance/helpers/batch_fix_devnotes_metadata.py"
    "maintenance/helpers/update_ruff_ignore.py"
    "tests/check_intermediate_results.py"
    "tests/example_strategies.py"
    "tests/run_examples_tests.sh"
    "tests/test_examples.py"
    "tests/test_examples_pytest.py"
    "tests/pytest.ini"
    "tests/conftest.py"
)

echo -e "${YELLOW}⚠️  以下文件将被删除（已备份）：${NC}"
echo ""
for file in "${FILES_TO_DELETE[@]}"; do
    echo "  - $file"
done
echo ""

read -p "确认继续? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}❌ 操作已取消${NC}"
    rm -rf "$BACKUP_DIR"
    exit 0
fi

echo ""
echo "📦 正在备份..."

# 备份并删除
DELETED_COUNT=0
BACKED_UP_COUNT=0

for file in "${FILES_TO_DELETE[@]}"; do
    full_path="$TOOLS_DIR/$file"
    
    if [ -f "$full_path" ]; then
        # 创建备份目录结构
        backup_file="$BACKUP_DIR/$file"
        mkdir -p "$(dirname "$backup_file")"
        
        # 备份
        cp "$full_path" "$backup_file"
        echo -e "${BLUE}📦${NC} 备份: $file"
        ((BACKED_UP_COUNT++))
        
        # 删除
        rm "$full_path"
        echo -e "${GREEN}✓${NC} 删除: $file"
        ((DELETED_COUNT++))
    else
        echo -e "${YELLOW}⊘${NC} 跳过（不存在）: $file"
    fi
done

# 删除 __pycache__
for pycache in "$TOOLS_DIR/tests/__pycache__" "$TOOLS_DIR/maintenance/helpers/__pycache__"; do
    if [ -d "$pycache" ]; then
        # 备份 __pycache__
        rel_path="${pycache#$TOOLS_DIR/}"
        backup_pycache="$BACKUP_DIR/$rel_path"
        mkdir -p "$(dirname "$backup_pycache")"
        cp -r "$pycache" "$backup_pycache"
        
        echo -e "${BLUE}📦${NC} 备份: $rel_path"
        ((BACKED_UP_COUNT++))
        
        # 删除
        rm -rf "$pycache"
        echo -e "${GREEN}✓${NC} 删除: $rel_path"
        ((DELETED_COUNT++))
    fi
done

echo ""
echo "=" * 80
echo -e "${GREEN}✅ 清理完成！${NC}"
echo ""
echo "📊 统计："
echo "   • 备份文件: $BACKED_UP_COUNT 个"
echo "   • 删除文件: $DELETED_COUNT 个"
echo "   • 备份位置: $BACKUP_DIR"
echo ""
echo "📝 后续步骤："
echo "   1. 测试新的 CLI 命令是否正常工作"
echo "   2. 确认无问题后，可以删除备份目录"
echo "   3. 如需恢复，请从备份目录复制回去"
echo ""
echo "🔧 新用法："
echo "   sage-dev maintenance organize-devnotes"
echo "   sage-dev maintenance fix-metadata"
echo "   sage-dev maintenance update-ruff-ignore"
echo "   sage-dev examples analyze"
echo ""
echo "🗑️  删除备份："
echo "   rm -rf $BACKUP_DIR"
echo ""
echo "=" * 80
