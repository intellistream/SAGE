#!/usr/bin/env bash
# Wrapper around sage-dev quality fix
# Keeps backward compatibility with old workflows

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v sage-dev >/dev/null 2>&1; then
	echo "❌ 未检测到 sage-dev 命令"
	echo "➡️  请先安装/激活开发环境: pip install -e packages/sage-tools"
	exit 1
fi

cd "$REPO_ROOT"

echo "🔧 Running 'sage-dev quality fix'..."
sage-dev quality fix "$@"

echo ""
echo "✅ Code quality fixes applied via sage-dev"
