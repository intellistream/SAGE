#!/bin/bash
# 🎯 最终验证脚本（Legacy Diagnostic Script）
set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$PROJECT_ROOT"
echo "🔍 最终验证 (legacy)"

missing=0
for f in pyproject.toml .github/workflows/ci.yml; do
  if [ -f "$f" ]; then echo "✅ 存在: $f"; else echo "❌ 缺失: $f"; missing=$((missing+1)); fi
done

if [ $missing -eq 0 ]; then
  echo "✅ 基础文件检查通过"
else
  echo "❌ 基础文件缺失: $missing"; exit 1
fi

echo "✅ 最终验证完成"
