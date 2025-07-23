#!/bin/bash

# SAGE System Environment Configuration
# 环境变量和默认配置

# === Ray Configuration ===
export RAY_HEAD_PORT=${RAY_HEAD_PORT:-10001}           # GCS server port
export RAY_CLIENT_PORT=${RAY_CLIENT_PORT:-10002}       # Client server port
export RAY_DASHBOARD_PORT=${RAY_DASHBOARD_PORT:-8265}  # Dashboard port
export RAY_TEMP_DIR=${RAY_TEMP_DIR:-/var/lib/ray_shared}
export RAY_RESOURCES=${RAY_RESOURCES:-'{"jobmanager": 1.0}'}

# === Daemon Configuration ===
export DAEMON_HOST=${DAEMON_HOST:-127.0.0.1}
export DAEMON_PORT=${DAEMON_PORT:-19001}
export ACTOR_NAME=${ACTOR_NAME:-sage_global_jobmanager}
export NAMESPACE=${NAMESPACE:-sage_system}

# === Path Configuration ===
export SAGE_HOME=${SAGE_HOME:-$(dirname $(dirname $(realpath $0)))}
export SAGE_LOG_DIR=${SAGE_LOG_DIR:-$SAGE_HOME/logs}
export SAGE_PID_DIR=${SAGE_PID_DIR:-/tmp/sage}
export SAGE_TEMP_DIR=${SAGE_TEMP_DIR:-/tmp/sage}

# === Logging Configuration ===
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export LOG_MAX_SIZE=${LOG_MAX_SIZE:-100MB}
export LOG_BACKUP_COUNT=${LOG_BACKUP_COUNT:-5}

# === System Configuration ===
export STARTUP_TIMEOUT=${STARTUP_TIMEOUT:-30}
export HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-10}
export SHUTDOWN_TIMEOUT=${SHUTDOWN_TIMEOUT:-15}

# === CLI Configuration ===
export CLI_SYMLINK_PATH=${CLI_SYMLINK_PATH:-/usr/local/bin/sage-jm}

# Create necessary directories
create_directories() {
    local dirs=("$SAGE_LOG_DIR" "$SAGE_PID_DIR" "$SAGE_TEMP_DIR")
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir" 2>/dev/null || sudo mkdir -p "$dir"
        fi
    done
}
