#!/bin/bash

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SAGE_ROOT/.sage/logs/install.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Install log not found: $LOG_FILE"
    exit 1
fi

python3 "$SAGE_ROOT/tools/install/log_analyzer.py" "$LOG_FILE"
