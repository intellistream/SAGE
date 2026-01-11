#!/usr/bin/env bash
# Pre-commit hook: 检测 sage-libs 是否违规导入 sage.middleware
#
# 根据 SAGE 架构规则：
# - L3 (sage-libs) 不得导入 L4 (sage-middleware)
# - 任何需要向上调用 (VectorDB, Memory, Refiner) 的代码必须放在 middleware
#
# 参考：docs-public/docs_src/dev-notes/cross-layer/MIDDLEWARE_COMPONENT_PROMOTION_POLICY.md

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root" || exit 1

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

LIBS_SRC="packages/sage-libs/src"

# 检查目录是否存在
if [[ ! -d "$LIBS_SRC" ]]; then
  exit 0
fi

# 支持 --all-files 参数
ALL_FILES=false
if [[ "${1:-}" == "--all-files" ]] || [[ -n "${PRE_COMMIT_FROM_REF:-}" ]]; then
  ALL_FILES=true
fi

# 获取要检查的文件
if [[ "$ALL_FILES" == "true" ]]; then
  # 检查所有文件
  files_to_check=$(find "$LIBS_SRC" -name "*.py" -type f | grep -v "__pycache__" || true)
else
  # Normal commit mode - check staged files only
  staged_files=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
  if [[ -z "$staged_files" ]]; then
    exit 0
  fi
  files_to_check=$(echo "$staged_files" | grep "^$LIBS_SRC/.*\.py$" || true)
fi

if [[ -z "$files_to_check" ]]; then
  exit 0
fi

violations=""

# 使用 Python AST 解析检查导入
check_imports() {
  local file="$1"
  python3 -c "
import ast
import sys

try:
    with open('$file', 'r') as f:
        tree = ast.parse(f.read())
except SyntaxError:
    sys.exit(0)

violations = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            if 'sage.middleware' in alias.name:
                violations.append(f'Line {node.lineno}: import {alias.name}')
    elif isinstance(node, ast.ImportFrom):
        if node.module and 'sage.middleware' in node.module:
            names = ', '.join(a.name for a in node.names)
            violations.append(f'Line {node.lineno}: from {node.module} import {names}')

if violations:
    for v in violations:
        print(v)
    sys.exit(1)
sys.exit(0)
" 2>/dev/null
}

# 检查每个文件
while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  [[ ! -f "$file" ]] && continue

  result=$(check_imports "$file" 2>&1) || {
    if [[ -n "$result" ]]; then
      violations="${violations}${file}:\n${result}\n\n"
    fi
  }
done <<< "$files_to_check"

if [[ -n "$violations" ]]; then
  echo ""
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${RED}❌ L3 → L4 架构违规检测到！${NC}"
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo -e "${YELLOW}规则：${NC} sage-libs (L3) 不得导入 sage.middleware (L4)"
  echo ""
  echo -e "${YELLOW}违规详情：${NC}"
  echo -e "$violations"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo -e "${YELLOW}💡 解决方案：${NC}"
  echo ""
  echo "1. 如果代码需要调用 VectorDB/Memory/Refiner 等后端服务："
  echo "   → 将代码移动到 sage-middleware/components/ 或 sage-middleware/operators/"
  echo ""
  echo "2. 如果只是类型提示或接口定义："
  echo "   → 使用 TYPE_CHECKING 条件导入"
  echo "   → 或在 sage-common/sage-platform 定义抽象接口"
  echo ""
  echo "3. 参考策略文档："
  echo "   → docs-public/docs_src/dev-notes/cross-layer/MIDDLEWARE_COMPONENT_PROMOTION_POLICY.md"
  echo ""
  echo -e "${RED}提交已被阻止以保护架构完整性。${NC}"
  echo ""
  exit 1
fi

echo -e "${GREEN}✓ sage-libs 架构检查通过${NC}"
exit 0
