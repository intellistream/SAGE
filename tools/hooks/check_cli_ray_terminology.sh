#!/usr/bin/env bash
# Pre-commit hook: 检测 sage-cli 中用户可见字符串是否残留 "Ray" 术语
#
# 根据 SAGE Issue #1438 (Align SAGE CLI and API Surfaces with Flownet Semantics):
# - sage-cli 的用户可见帮助文本、echo 消息、docstring 不得含有 "Ray" 术语
# - 内部实现注释 (# ...) 和向后兼容查找逻辑允许保留
#
# 参考：docs-public/docs_src/dev-notes/cross-layer/
#       .github/copilot-instructions.md (Flownet Migration Baseline)
#
# 可检测的违规模式（用户可见字符串）：
#   help="... Ray ..."
#   typer.echo("... Ray ...")
#   """...\n..Ray..."""  (module/function docstrings)
#
# 允许的例外（不触发告警）：
#   # 注释行中的 "Ray"
#   ray_version_checker.py (已弃用但保留兼容)
#   "import ray" (向后兼容检测代码)
#   get('ray_command', ...) (向后兼容键名查找)

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root" || exit 1

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CLI_SRC="packages/sage-cli/src/sage/cli"

# 检查目录是否存在
if [[ ! -d "$CLI_SRC" ]]; then
  echo -e "${YELLOW}⚠️  sage-cli 目录不存在: $CLI_SRC，跳过检查${NC}"
  exit 0
fi

# 支持 --all-files 参数
ALL_FILES=false
if [[ "${1:-}" == "--all-files" ]] || [[ -n "${PRE_COMMIT_FROM_REF:-}" ]]; then
  ALL_FILES=true
fi

# 获取要检查的文件
if [[ "$ALL_FILES" == "true" ]]; then
  files_to_check=$(find "$CLI_SRC" -name "*.py" -type f | grep -v "__pycache__" | grep -v "ray_version_checker.py" || true)
else
  staged_files=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
  if [[ -z "$staged_files" ]]; then
    exit 0
  fi
  files_to_check=$(echo "$staged_files" | grep "^$CLI_SRC/.*\.py$" | grep -v "ray_version_checker.py" || true)
fi

if [[ -z "$files_to_check" ]]; then
  exit 0
fi

violations=""
violation_count=0

# 检查用户可见的 typer/CLI 相关字符串中的 Ray 术语
# 只检查以下模式（用户直接看到的）：
#   1. typer.echo("... Ray ...")           -- 用户终端输出
#   2. help="... Ray ..."                  -- CLI help 文本
#   3. """docstring ... Ray ...""" 在命令函数的第一个字符串   -- 命令描述
# 不检查：bash heredoc 字符串、内部函数文档、兼容性注释
check_file() {
  local file="$1"

  local result
  result=$(python3 - "$file" << 'PYEOF'
import ast
import sys
import re

file_path = sys.argv[1]

ALLOWED_PATTERNS = [
    'ray_command',          # 向后兼容键名查找
    'ray_version_checker',  # 已弃用兼容文件
    'import ray',           # 向后兼容检测代码
    'isage-flow',           # 安装说明
    'flownet',              # 包含 flownet 的描述
    'legacy',               # 明确标注 legacy/过渡
    '过渡',                 # 过渡期说明
    '兼容',                 # 兼容性说明
    'ray (legacy)',         # 明确 legacy 标注
    'ray (将废弃',          # 废弃说明
]

# 识别 bash heredoc 字符串的模式（这些不是用户可见的 CLI 文本）
BASH_HEREDOC_PATTERNS = [
    'tee -a',           # bash heredoc 日志命令
    'echo "[info]',     # bash INFO 日志
    'echo "[success]',  # bash SUCCESS 日志
    'echo "[error]',    # bash ERROR 日志
    'echo "[warning]',  # bash WARNING 日志
    '$ray_cmd',         # bash 变量引用
    '#!/',              # bash shebang
    'pgrep -f',         # bash 进程检查
    '| tee',            # bash tee 管道
]

with open(file_path, 'r', encoding='utf-8') as f:
    source = f.read()

try:
    tree = ast.parse(source)
except SyntaxError:
    sys.exit(0)

violations = []

# 只检查特定的 AST 节点模式（不检查任意字符串）
for node in ast.walk(tree):
    # 模式1: typer.echo() 调用
    if isinstance(node, ast.Call):
        # 检查 typer.echo(...)
        is_typer_echo = False
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == 'echo'
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == 'typer'):
            is_typer_echo = True
        # 检查 console.print(...) 在 doctor.py
        is_console_print = False
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == 'print'
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == 'console'):
            is_console_print = True

        if is_typer_echo or is_console_print:
            for arg in node.args:
                val = None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    val = arg.value
                elif isinstance(arg, ast.JoinedStr):
                    # f-string: reconstruct format string parts
                    parts = []
                    for v in arg.values:
                        if isinstance(v, ast.Constant) and isinstance(v.value, str):
                            parts.append(v.value)
                    val = ''.join(parts)
                if val and 'Ray' in val:
                    is_allowed = any(p.lower() in val.lower() for p in ALLOWED_PATTERNS)
                    is_bash = any(p.lower() in val.lower() for p in BASH_HEREDOC_PATTERNS)
                    if not is_allowed and not is_bash:
                        violations.append((node.lineno, repr(val[:100])))

    # 模式2: keyword help="..." in command/option definitions
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if kw.arg == 'help' and isinstance(kw.value, ast.Constant):
                val = kw.value.value
                if isinstance(val, str) and 'Ray' in val:
                    is_allowed = any(p.lower() in val.lower() for p in ALLOWED_PATTERNS)
                    if not is_allowed:
                        violations.append((node.lineno, repr(val[:100])))

    # 模式3: 命令函数的 docstring（第一个语句是字符串常量）
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # 只检查带 @app.command 装饰器的函数（命令函数）
        is_command = any(
            (isinstance(d, ast.Call)
             and isinstance(d.func, ast.Attribute)
             and d.func.attr == 'command')
            or
            (isinstance(d, ast.Attribute) and d.attr == 'command')
            for d in node.decorator_list
        )
        if is_command and node.body:
            first_stmt = node.body[0]
            if (isinstance(first_stmt, ast.Expr)
                    and isinstance(first_stmt.value, ast.Constant)
                    and isinstance(first_stmt.value.value, str)):
                val = first_stmt.value.value
                if 'Ray' in val:
                    is_allowed = any(p.lower() in val.lower() for p in ALLOWED_PATTERNS)
                    if not is_allowed:
                        violations.append((first_stmt.lineno, repr(val[:100])))

for lineno, val in violations:
    print(f'{file_path}:{lineno}: 发现 Ray 术语: {val}')
PYEOF
2>/dev/null || true)

  if [[ -n "$result" ]]; then
    echo "$result"
    return 1
  fi
  return 0
}

echo -e "${BLUE}🔍 检查 sage-cli 用户可见字符串中的 Ray 术语...${NC}"

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  if ! output=$(check_file "$file"); then
    violations+="$output"$'\n'
    ((violation_count++)) || true
  fi
done <<< "$files_to_check"

if [[ -n "$violations" ]]; then
  echo ""
  echo -e "${RED}❌ 在 sage-cli 用户可见字符串中发现 Ray 术语（违反 Issue #1438）：${NC}"
  echo ""
  echo "$violations"
  echo -e "${YELLOW}修复方式：${NC}"
  echo "  1. 将 'Ray' 替换为 'Flownet' 或 'SAGE 运行时' 或 'SAGE集群'"
  echo "  2. 若确实需要保留（如向后兼容注释），请添加到此脚本的 ALLOWED_PATTERNS 中"
  echo "  3. 参考 docs-public/docs_src/dev-notes/cross-layer/ 中的 Flownet 迁移指南"
  echo ""
  echo -e "${YELLOW}允许的例外（无需修改）：${NC}"
  echo "  - 代码注释 (# ...)"
  echo "  - ray_version_checker.py (已弃用的向后兼容文件)"
  echo "  - 'import ray' 检测逻辑"
  echo "  - 兼容性键名查找 get('ray_command', ...)"
  exit 1
fi

echo -e "${GREEN}✅ sage-cli 用户可见字符串中未发现 Ray 术语${NC}"
exit 0
