#!/usr/bin/env bash
# Update documentation to remove references to deleted commands
# Commands removed: serve, run, stop, restart, status, logs

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "🔍 Searching for references to removed commands..."

# Find all markdown files with references
FILES=$(rg "sage llm (serve|run|stop|restart|status|logs)" --type md --files-with-matches || true)

if [ -z "$FILES" ]; then
    echo "✅ No references found"
    exit 0
fi

echo "📝 Found $(echo "$FILES" | wc -l) files to update"
echo ""

# Create migration message
MIGRATION_MSG="
**⚠️ 命令已移除**: \`sage llm serve/run/stop/restart/status/logs\` 已被移除。

**正确用法** (100% Control Plane):
\`\`\`bash
# 启动 Gateway（包含 Control Plane）
sage gateway start

# 启动引擎
sage llm engine start <model> --engine-kind llm
sage llm engine start <model> --engine-kind embedding --use-gpu

# 查看引擎状态
sage llm engine list

# 停止引擎
sage llm engine stop <engine-id>
\`\`\`

**Python 客户端**:
\`\`\`python
from sage.llm import UnifiedInferenceClient

# 自动连接 Control Plane
client = UnifiedInferenceClient.create()
response = client.chat([{\"role\": \"user\", \"content\": \"Hello\"}])
\`\`\`
"

echo "📄 Files to update:"
echo "$FILES"
echo ""
echo "ℹ️  Manual review required for each file"
echo "   This script only identifies files - update them manually"
echo "   considering each file's context."
echo ""
echo "Migration message template:"
echo "$MIGRATION_MSG"
