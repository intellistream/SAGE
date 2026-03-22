#!/bin/bash
# 🛠️ SAGE 管理脚本入口
# 简化后的入口，主要用于 Git hooks 设置和项目维护

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAINTENANCE_SCRIPT="$SCRIPT_DIR/tools/maintenance/sage-maintenance.sh"

if [ ! -f "$MAINTENANCE_SCRIPT" ]; then
    echo "Maintenance script not found at $MAINTENANCE_SCRIPT" >&2
    exit 1
fi

if [[ "$1" = "-h" || "$1" = "--help" ]]; then
    echo "Usage: ./manage.sh [maintenance-command]"
    echo ""
    echo "Examples:"
    echo "  ./manage.sh              # Setup Git hooks"
    echo "  ./manage.sh clean        # Clean build artifacts"
    echo "  ./manage.sh doctor       # Run health check"
    echo ""
    echo "This script forwards all arguments to tools/maintenance/sage-maintenance.sh."
    exit 0
fi

# 无参数时默认设置 Git hooks
if [ $# -eq 0 ]; then
    echo "Configuring Git hooks..."
    if ! bash "$MAINTENANCE_SCRIPT" --force setup-hooks; then
        echo "Git hooks setup failed" >&2
        exit 1
    fi
    exit 0
fi

# Additional maintenance helpers
if [ "$1" = "clean-env" ] || [ "$1" = "uninstall" ]; then
    # Provide a straightforward alias to the uninstall/cleanup helper
    CLEAN_SCRIPT="$SCRIPT_DIR/tools/install/cleanup/uninstall_sage.sh"
    if [ -f "$CLEAN_SCRIPT" ]; then
        exec bash "$CLEAN_SCRIPT" "${@:2}"
    else
        echo "Cleanup script not found at $CLEAN_SCRIPT" >&2
        exit 1
    fi
fi

exec bash "$MAINTENANCE_SCRIPT" "$@"
