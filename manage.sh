#!/bin/bash
# Thin wrapper around maintenance utilities for discoverability.

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
    echo "  ./manage.sh              # Bootstrap all submodules"
    echo "  ./manage.sh submodule status"
    echo "  ./manage.sh clean"
    echo ""
    echo "This script forwards all arguments to tools/maintenance/sage-maintenance.sh."
    exit 0
fi

if [ $# -eq 0 ]; then
    cleanup_needed=false

    if git config --local --get "submodule.packages/sage-middleware/src/sage/middleware/components/sage_db.url" &>/dev/null; then
        cleanup_needed=true
    elif git config --local --get "submodule.packages/sage-middleware/src/sage/middleware/components/sage_flow.url" &>/dev/null; then
        cleanup_needed=true
    elif git config --local --get "submodule.packages/sage-middleware/src/sage/middleware/components/sage_vllm.url" &>/dev/null; then
        cleanup_needed=true
    fi

    if [ "$cleanup_needed" = true ]; then
        echo "Detected legacy submodule config; running cleanup + bootstrap..."
        if ! bash "$MAINTENANCE_SCRIPT" submodule cleanup; then
            echo "Submodule cleanup failed" >&2
            exit 1
        fi
        if ! bash "$MAINTENANCE_SCRIPT" submodule bootstrap; then
            echo "Submodule bootstrap failed" >&2
            exit 1
        fi
    else
        if ! bash "$MAINTENANCE_SCRIPT" submodule bootstrap; then
            echo "Submodule bootstrap failed" >&2
            exit 1
        fi
    fi

    echo "Configuring Git hooks..."
    if ! bash "$MAINTENANCE_SCRIPT" setup-hooks --force; then
        echo "Git hooks setup failed" >&2
        exit 1
    fi
    exit 0
fi

exec bash "$MAINTENANCE_SCRIPT" "$@"
