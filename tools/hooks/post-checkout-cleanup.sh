#!/usr/bin/env bash
# Git post-checkout hook: 自动清理未追踪的目录（分支切换后）
#
# 这个 hook 在分支切换后运行，自动清理那些在当前分支中被删除
# 但在工作目录中仍然存在的目录（untracked directories）。
#
# 常见场景：
# - 在 feature 分支中移动/删除了目录
# - 切换回 main-dev 分支
# - Git 不会自动删除这些目录，导致 untracked files
#
# 这个 hook 会自动检测并清理这些目录

set -euo pipefail

# Git 传递的参数
old_ref="$1"
new_ref="$2"
checkout_type="$3"  # 1 = 分支切换, 0 = 文件 checkout

# 只在分支切换时运行（checkout_type == 1）
if [[ "$checkout_type" != "1" ]]; then
  exit 0
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root" || exit 0

# 配置：需要自动清理的 untracked 目录模式
# 使用数组存储需要检查的路径模式
CLEANUP_PATTERNS=(
  "packages/sage-common/src/sage/common/components/sage_llm"
  "packages/sage-llm-core/src/sage/llm/engines/sagellm"
  # 可以添加更多需要自动清理的路径
)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否有未追踪的目录需要清理
untracked_dirs=()
for pattern in "${CLEANUP_PATTERNS[@]}"; do
  if [[ -d "$pattern" ]]; then
    # 检查这个目录是否被 Git 追踪
    if ! git ls-files --error-unmatch "$pattern" >/dev/null 2>&1; then
      untracked_dirs+=("$pattern")
    fi
  fi
done

# 如果没有需要清理的目录，直接退出
if [[ ${#untracked_dirs[@]} -eq 0 ]]; then
  exit 0
fi

# 显示发现的未追踪目录
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🧹 检测到未追踪的目录（分支切换后遗留）${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}以下目录在当前分支中不存在，但在工作目录中仍然存在：${NC}"
echo ""
for dir in "${untracked_dirs[@]}"; do
  echo -e "  ${RED}✗${NC} $dir"
done
echo ""

# 询问用户是否自动清理
read -p "$(echo -e "${GREEN}是否自动清理这些目录？${NC} [Y/n] ")" -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
  # 用户确认清理
  echo ""
  echo -e "${GREEN}正在清理...${NC}"
  echo ""

  for dir in "${untracked_dirs[@]}"; do
    if rm -rf "$dir"; then
      echo -e "  ${GREEN}✓${NC} 已删除: $dir"
    else
      echo -e "  ${RED}✗${NC} 删除失败: $dir"
    fi
  done

  echo ""
  echo -e "${GREEN}✓ 清理完成！${NC}"
  echo ""
else
  # 用户拒绝清理
  echo ""
  echo -e "${YELLOW}已跳过自动清理。${NC}"
  echo ""
  echo -e "${BLUE}💡 提示：你可以手动清理这些目录：${NC}"
  echo ""
  for dir in "${untracked_dirs[@]}"; do
    echo -e "  rm -rf $dir"
  done
  echo ""
fi

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

exit 0
