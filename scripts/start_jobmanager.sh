#!/bin/bash
# filepath: /home/tjy/SAGE/scripts/start_jobmanager.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_SCRIPT="$SCRIPT_DIR/jobmanager_daemon.py"

# 检查并启动JobManager
echo "🚀 Checking JobManager service..."

python3 "$DAEMON_SCRIPT" ensure

if [ $? -eq 0 ]; then
    echo "✅ JobManager is running on 127.0.0.1:19000"
else
    echo "❌ Failed to start JobManager"
    exit 1
fi

# usage:
# # 给脚本执行权限
# chmod +x scripts/jobmanager_daemon.py
# chmod +x scripts/start_jobmanager.sh

# # 1. 检查并启动JobManager（推荐）
# python3 scripts/jobmanager_daemon.py ensure

# # 2. 使用bash脚本
# ./scripts/start_jobmanager.sh

# # 3. 其他命令
# python3 scripts/jobmanager_daemon.py status    # 查看状态
# python3 scripts/jobmanager_daemon.py stop      # 停止服务
# python3 scripts/jobmanager_daemon.py restart   # 重启服务
# python3 scripts/jobmanager_daemon.py start     # 启动服务