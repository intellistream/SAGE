#!/bin/bash
#
# Install Git Hooks for SAGE Development
#
# 为 SAGE 项目安装 Git hooks，包括架构合规性检查
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔧 安装 SAGE Git Hooks..."

# 获取项目根目录
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if [ ! -d "$ROOT_DIR/.git" ]; then
    echo -e "${RED}❌ 错误: 不在 Git 仓库中${NC}"
    exit 1
fi

HOOKS_DIR="$ROOT_DIR/.git/hooks"
SOURCE_DIR="$ROOT_DIR/tools/git-hooks"

# 检查源目录
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}❌ 错误: 找不到 hooks 源目录: $SOURCE_DIR${NC}"
    exit 1
fi

# 安装 pre-commit hook
echo ""
echo "📦 安装 pre-commit hook..."

PRE_COMMIT_SRC="$SOURCE_DIR/pre-commit"
PRE_COMMIT_DST="$HOOKS_DIR/pre-commit"

if [ ! -f "$PRE_COMMIT_SRC" ]; then
    echo -e "${RED}❌ 错误: 找不到 pre-commit 源文件${NC}"
    exit 1
fi

# 备份现有 hook
if [ -f "$PRE_COMMIT_DST" ] && [ ! -L "$PRE_COMMIT_DST" ]; then
    BACKUP="$PRE_COMMIT_DST.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}⚠️  备份现有 pre-commit hook 到: $BACKUP${NC}"
    mv "$PRE_COMMIT_DST" "$BACKUP"
fi

# 创建符号链接
ln -sf "../../tools/git-hooks/pre-commit" "$PRE_COMMIT_DST"
chmod +x "$PRE_COMMIT_SRC"

echo -e "${GREEN}✅ pre-commit hook 已安装${NC}"

# 测试 hook
echo ""
echo "🧪 测试 architecture checker..."
if python3 "$ROOT_DIR/tools/architecture_checker.py" --root "$ROOT_DIR" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Architecture checker 可用${NC}"
else
    echo -e "${YELLOW}⚠️  Architecture checker 测试失败，但 hook 已安装${NC}"
    echo "   您可能需要安装相关依赖"
fi

echo ""
echo "=" * 70
echo -e "${GREEN}✅ Git hooks 安装完成！${NC}"
echo ""
echo "以下 hooks 已激活:"
echo "  • pre-commit: 提交前检查架构合规性"
echo ""
echo "使用方法:"
echo "  • 正常提交: git commit -m 'message'"
echo "  • 跳过检查: git commit --no-verify -m 'message'"
echo "  • 卸载 hooks: rm .git/hooks/pre-commit"
echo ""
echo "详细信息请查看: docs/PACKAGE_ARCHITECTURE.md"
echo "=" * 70
