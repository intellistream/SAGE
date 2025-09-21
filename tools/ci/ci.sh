#!/usr/bin/env bash
# Unified CI/CI-CD entrypoint for SAGE
#
# Subcommands:
#   run           Run local CI (real execution) — wraps run_local_ci.sh
#   act           Execute GitHub Actions workflow using `act` (if installed)
#   help          Show this help
#
# Examples:
#   tools/ci/ci.sh run
#   BUILD_CPP_DEPS=0 tools/ci/ci.sh run
#   tools/ci/ci.sh diag
#   tools/ci/ci.sh act -j test

set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

SCRIPT_DIR_CI="$ROOT_DIR/tools/ci"

usage() {
  cat <<'USAGE'
Usage: tools/ci/ci.sh <subcommand> [args]

Subcommands:
  run           Run local CI (real execution) — dev install, optional deps, examples, imports
  act [args]    Run the GitHub Actions workflow locally using `act`
  help          Show this help

Environment variables for `run`:
  PYTHON_BIN, BUILD_CPP_DEPS, RUN_EXAMPLES, RUN_CODE_QUALITY, RUN_IMPORT_TESTS, RUN_PYPI_VALIDATE

Examples:
  tools/ci/ci.sh run
  BUILD_CPP_DEPS=0 RUN_EXAMPLES=0 tools/ci/ci.sh run
  tools/ci/ci.sh act -j test
USAGE
}

subcmd="${1:-help}"
shift || true

case "$subcmd" in
  run)
    exec bash "$SCRIPT_DIR_CI/run_local_ci.sh" "$@"
    ;;
  act)
    if ! command -v act >/dev/null 2>&1; then
      echo "'act' is not installed. See https://github.com/nektos/act"
      exit 1
    fi
    # Default job is 'test' if none provided
    if [[ $# -eq 0 ]]; then
      set -- -j test
    fi
    exec act "$@"
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    echo "Unknown subcommand: $subcmd" >&2
    usage
    exit 1
    ;;
esac
