#!/bin/bash
# ⚡ 轻量级CI验证工具（Legacy Diagnostic Script）
set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$PROJECT_ROOT"
echo "🔧 轻量CI验证 (legacy)"

check() { grep -q "$1" .github/workflows/ci.yml && echo "✅ $2" || echo "❌ $2"; }

check "actions/checkout@" "包含 checkout step"
check "actions/setup-python@" "包含 setup-python step"
check "quickstart.sh" "包含 quickstart 脚本调用"

echo "📦 子包结构检查"
for pkg in packages/*; do
  [ -d "$pkg" ] || continue
  [ -f "$pkg/pyproject.toml" ] && echo "✅ $(basename "$pkg") 有 pyproject.toml" || echo "⚠️ $(basename "$pkg") 缺少 pyproject.toml"
done
echo "✅ 轻量CI验证完成"
