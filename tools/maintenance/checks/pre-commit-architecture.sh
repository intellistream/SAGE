#!/usr/bin/env bash
# Pre-commit hook: 检测并阻止提交错误位置的目录
#
# 这个 hook 在 commit 前运行，检测是否有违反架构的目录结构
# 例如：防止提交已独立为 PyPI 包的组件的源码

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root" || exit 1

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 定义架构违规的路径模式
# 格式：错误路径|正确路径|描述
# 注意：sageLLM 已独立为 PyPI 包（pip install isage-sagellm），不应再有源码
ARCHITECTURE_VIOLATIONS=(
  "src/sage/common/components/sage_llm|REMOVED|sageLLM 已独立为 PyPI 包（pip install isage-sagellm）"
  "src/sage/common/components/sageLLM|REMOVED|sageLLM 已独立为 PyPI 包（pip install isage-sagellm）"
  "src/sage/llm/sageLLM|REMOVED|sageLLM 已独立为 PyPI 包（pip install isage-sagellm）"
  # 可以添加更多架构规则
)

violations_found=false

# 检查暂存区中的文件
staged_files=$(git diff --cached --name-only)

if [[ -z "$staged_files" ]]; then
  exit 0
fi

# 检查每个架构违规规则
for rule in "${ARCHITECTURE_VIOLATIONS[@]}"; do
  IFS='|' read -r wrong_path correct_path description <<< "$rule"

  # 检查暂存区中是否有违规路径的文件
  if echo "$staged_files" | grep -q "^$wrong_path/"; then
    if [[ "$violations_found" == "false" ]]; then
      echo ""
      echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
      echo -e "${RED}❌ 架构违规检测到！${NC}"
      echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
      echo ""
      violations_found=true
    fi

    echo -e "${YELLOW}违规路径：${NC} $wrong_path"
    echo -e "${GREEN}正确路径：${NC} $correct_path"
    echo -e "${BLUE}说明：${NC} $description"
    echo ""

    # 显示违规的文件
    echo -e "${YELLOW}违规文件：${NC}"
    echo "$staged_files" | grep "^$wrong_path/" | sed 's/^/  /'
    echo ""
  fi
done

if [[ "$violations_found" == "true" ]]; then
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo -e "${YELLOW}💡 解决方案：${NC}"
  echo ""
  echo "1. 取消暂存这些文件："
  echo "   git reset HEAD <file>"
  echo ""
  echo "2. 移动到正确的位置"
  echo ""
  echo "3. 或者，如果这是需要删除的旧目录，运行："
  echo "   git rm -r <wrong_path>"
  echo ""
  echo -e "${RED}提交已被阻止以保护架构完整性。${NC}"
  echo ""

  exit 1
fi

exit 0
