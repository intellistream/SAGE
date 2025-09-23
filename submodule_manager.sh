#!/usr/bin/env bash

# Thin wrapper to the real submodule manager under tools/maintenance
# Usage:
#   bash submodule_manager.sh [command]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec bash "$SCRIPT_DIR/tools/maintenance/submodule_manager.sh" "$@"
