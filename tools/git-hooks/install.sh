#!/bin/bash
#
# Install Git Hooks for sage-development
#
# 为 SAGE 项目安装 Git hooks，包括架构合规性检查
#
# 使用方法:
#   ./install.sh           # 正常模式（显示详细输出）
#   ./install.sh --quiet   # 静默模式（仅显示错误）
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否是静默模式
QUIET_MODE=false
if [[ "$1" == "--quiet" ]] || [[ "$1" == "-q" ]]; then
    QUIET_MODE=true
fi

# 输出函数（静默模式下不输出）
print_info() {
    if [ "$QUIET_MODE" = false ]; then
        echo "$@"
    fi
}

print_success() {
    if [ "$QUIET_MODE" = false ]; then
        echo -e "${GREEN}$*${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}$*${NC}"
}

print_error() {
    echo -e "${RED}$*${NC}"
}

print_info "🔧 安装 SAGE Git Hooks..."

# 获取项目根目录
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

if [ ! -d "$ROOT_DIR/.git" ]; then
    print_error "❌ 错误: 不在 Git 仓库中"
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
print_info ""
print_info "📦 安装 pre-commit hook..."

PRE_COMMIT_SRC="$SOURCE_DIR/pre-commit"
PRE_COMMIT_DST="$HOOKS_DIR/pre-commit"

if [ ! -f "$PRE_COMMIT_SRC" ]; then
    print_error "❌ 错误: 找不到 pre-commit 源文件"
    exit 1
fi

# 备份现有 hook
if [ -f "$PRE_COMMIT_DST" ] && [ ! -L "$PRE_COMMIT_DST" ]; then
    BACKUP="$PRE_COMMIT_DST.backup.$(date +%Y%m%d_%H%M%S)"
    print_warning "⚠️  备份现有 pre-commit hook 到: $(basename $BACKUP)"
    mv "$PRE_COMMIT_DST" "$BACKUP"
fi

# 创建符号链接
ln -sf "../../tools/git-hooks/pre-commit" "$PRE_COMMIT_DST"
chmod +x "$PRE_COMMIT_SRC"

print_success "✅ pre-commit hook 已安装"

# 安装 pre-commit 框架（如果已安装 Python 包）
print_info ""
print_info "📦 检查 pre-commit 框架..."

if command -v pre-commit >/dev/null 2>&1; then
    print_info "   pre-commit 已安装，配置 hooks..."
    cd "$ROOT_DIR"
    if pre-commit install --config tools/pre-commit-config.yaml --install-hooks >/dev/null 2>&1; then
        print_success "✅ pre-commit 框架已配置"
    else
        print_warning "⚠️  pre-commit 框架配置失败"
    fi
else
    print_warning "⚠️  pre-commit 未安装"
    print_info "   代码质量检查将被跳过"
    print_info "   安装: pip install pre-commit"
fi

# 测试 hook
if [ "$QUIET_MODE" = false ]; then
    print_info ""
    print_info "🧪 测试 architecture checker..."
    if python3 "$ROOT_DIR/tools/architecture_checker.py" --root "$ROOT_DIR" >/dev/null 2>&1; then
        print_success "✅ Architecture checker 可用"
    else
        print_warning "⚠️  Architecture checker 测试失败，但 hook 已安装"
        print_info "   您可能需要安装相关依赖"
    fi

    print_info ""
    print_info "======================================================================"
    print_success "✅ Git hooks 安装完成！"
    print_info ""
    print_info "以下功能已激活:"
    print_info "  • 代码质量检查: black, isort, ruff, mypy（需要 pre-commit）"
    print_info "  • Dev-notes 文档规范检查: 分类、元数据等"
    print_info "  • 架构合规性检查: 包依赖、导入路径等"
    print_info ""
    print_info "使用方法:"
    print_info "  • 正常提交: git commit -m 'message'"
    print_info "  • 跳过检查: git commit --no-verify -m 'message'"
    print_info "  • 安装代码检查工具: pip install pre-commit"
    print_info ""
    print_info "相关文档:"
    print_info "  • 架构规范: docs-public/docs_src/dev-notes/package-architecture.md"
    print_info "  • 文档模板: docs/dev-notes/TEMPLATE.md"
    print_info "======================================================================"
fi

exit 0
