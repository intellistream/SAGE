#!/usr/bin/env bash
# ============================================================================
# 移除 LibAMM Submodule 脚本
# ============================================================================
#
# 用途：从 SAGE 仓库中移除 libamm git submodule
# 前提：isage-libamm 已成功上传到 PyPI
#
# 使用方法：
#   ./tools/scripts/remove_libamm_submodule.sh
#
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LIBAMM_PATH="packages/sage-libs/src/sage/libs/libamm"

echo "============================================================================"
echo "  移除 LibAMM Submodule"
echo "============================================================================"
echo ""

cd "$SAGE_ROOT"

# 步骤 1：检查是否是 git submodule
echo "📋 步骤 1：检查 libamm submodule 状态..."
if [ -f ".gitmodules" ] && grep -q "libamm" .gitmodules; then
    echo "   ✓ 找到 libamm submodule 配置"
else
    echo "   ⚠️  警告：.gitmodules 中未找到 libamm 配置"
    echo "   继续检查目录..."
fi

if [ -d "$LIBAMM_PATH" ]; then
    echo "   ✓ 找到 libamm 目录: $LIBAMM_PATH"
else
    echo "   ✗ 错误：未找到 libamm 目录"
    exit 1
fi

# 步骤 2：验证 PyPI 上的 isage-libamm
echo ""
echo "📦 步骤 2：验证 isage-libamm 在 PyPI 上可用..."
if pip index versions isage-libamm &>/dev/null; then
    echo "   ✓ isage-libamm 在 PyPI 上可用"
    pip index versions isage-libamm | head -2
else
    echo "   ✗ 错误：isage-libamm 在 PyPI 上不可用"
    echo "   请先上传 isage-libamm 到 PyPI"
    exit 1
fi

# 步骤 3：确认操作
echo ""
echo "⚠️  警告：此操作将："
echo "   1. 移除 git submodule 配置"
echo "   2. 删除 $LIBAMM_PATH 目录"
echo "   3. 清理 .git/modules 中的 submodule 数据"
echo ""
read -p "确认继续？[y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "   已取消操作"
    exit 0
fi

# 步骤 4：备份（可选）
echo ""
echo "💾 步骤 4：创建备份..."
BACKUP_DIR="/tmp/sage-libamm-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
if [ -d "$LIBAMM_PATH" ]; then
    cp -r "$LIBAMM_PATH" "$BACKUP_DIR/"
    echo "   ✓ 备份到: $BACKUP_DIR"
fi

# 步骤 5：移除 submodule
echo ""
echo "🗑️  步骤 5：移除 submodule..."

# 5.1 - Deinitialize submodule
if git config -f .gitmodules --get-regexp "submodule.*libamm" &>/dev/null; then
    echo "   → git submodule deinit -f $LIBAMM_PATH"
    git submodule deinit -f "$LIBAMM_PATH" || true
fi

# 5.2 - Remove from .gitmodules
if [ -f ".gitmodules" ]; then
    echo "   → 从 .gitmodules 中移除 libamm 配置"
    # 找到 libamm 相关的 section 并删除
    if grep -q "libamm" .gitmodules; then
        # 使用临时文件
        TEMP_FILE=$(mktemp)
        awk '/\[submodule.*libamm/,/^$/ {next} {print}' .gitmodules > "$TEMP_FILE"
        mv "$TEMP_FILE" .gitmodules
        git add .gitmodules
    fi
fi

# 5.3 - Remove from git index and working tree
echo "   → git rm -f $LIBAMM_PATH"
git rm -f "$LIBAMM_PATH" || true

# 5.4 - Clean .git/modules
GIT_MODULES_PATH=".git/modules/$LIBAMM_PATH"
if [ -d "$GIT_MODULES_PATH" ]; then
    echo "   → 清理 $GIT_MODULES_PATH"
    rm -rf "$GIT_MODULES_PATH"
fi

# 5.5 - Clean .git/config
if git config --get-regexp "submodule.*libamm" &>/dev/null; then
    echo "   → 清理 .git/config 中的 submodule 配置"
    git config --remove-section "submodule.$LIBAMM_PATH" 2>/dev/null || true
fi

echo "   ✓ Submodule 移除完成"

# 步骤 6：验证移除结果
echo ""
echo "🔍 步骤 6：验证移除结果..."
if [ -d "$LIBAMM_PATH" ]; then
    echo "   ✗ 错误：$LIBAMM_PATH 仍然存在"
    exit 1
else
    echo "   ✓ $LIBAMM_PATH 已删除"
fi

if git config -f .gitmodules --get-regexp "submodule.*libamm" &>/dev/null; then
    echo "   ⚠️  警告：.gitmodules 中仍有 libamm 配置"
else
    echo "   ✓ .gitmodules 已清理"
fi

# 步骤 7：显示状态
echo ""
echo "📊 步骤 7：Git 状态..."
git status --short

# 步骤 8：提示下一步
echo ""
echo "============================================================================"
echo "  ✅ LibAMM Submodule 移除完成"
echo "============================================================================"
echo ""
echo "📝 下一步操作："
echo ""
echo "1. 检查更改："
echo "   git status"
echo "   git diff --cached"
echo ""
echo "2. 提交更改："
echo "   git commit -m \"refactor: remove libamm submodule, use PyPI dependency"
echo ""
echo "   - Remove libamm submodule from sage-libs source tree"
echo "   - LibAMM is now maintained independently at intellistream/LibAMM"
echo "   - Users get libamm via PyPI: isage-libs → isage-libamm dependency"
echo "   - Reduces SAGE repository complexity and size"
echo ""
echo "   Benefits:"
echo "   - Clear separation of concerns"
echo "   - Easier maintenance (no submodule sync issues)"
echo "   - Faster clone/checkout (smaller repo)"
echo "   - LibAMM can evolve independently"
echo ""
echo "   PyPI: https://pypi.org/project/isage-libamm/\""
echo ""
echo "3. 更新 sage-libs 版本并重新发布："
echo "   # 编辑版本号"
echo "   vim packages/sage-libs/src/sage/libs/_version.py  # 改为 0.2.1"
echo ""
echo "   # 清理旧构建"
echo "   rm -rf ~/.sage/dist/sage-libs"
echo ""
echo "   # 重新构建并上传"
echo "   sage-dev package pypi build sage-libs --upload --no-dry-run"
echo ""
echo "4. 验证安装："
echo "   python -m venv /tmp/test-sage-libs"
echo "   source /tmp/test-sage-libs/bin/activate"
echo "   pip install isage-libs"
echo "   python -c \"import PyAMM; print('✅ LibAMM from PyPI works')\""
echo ""
echo "💾 备份位置: $BACKUP_DIR"
echo "   (如需回滚，可以从这里恢复)"
echo ""
