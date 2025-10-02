#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./tools/maintenance/setup_hooks.sh [options]

Install tracked Git hook samples into the local .git/hooks directory.

Options:
  -h, --help          Show this help message and exit
  --hook NAME         Hook filename to install (default: post-checkout)
  -f, --force         Overwrite existing hook file if present
EOF
}

HOOK_NAME="post-checkout"
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --hook)
      if [[ $# -lt 2 ]]; then
        echo "[setup_hooks] Missing value for --hook" >&2
        exit 1
      fi
      HOOK_NAME="$2"
      shift 2
      ;;
    -f|--force)
      FORCE=true
      shift
      ;;
    *)
      echo "[setup_hooks] Unknown option: $1" >&2
      echo >&2
      usage >&2
      exit 1
      ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "[setup_hooks] Unable to detect repository root. Run inside a Git repository." >&2
  exit 1
fi

SAMPLE_PATH="$REPO_ROOT/tools/maintenance/git-hooks/$HOOK_NAME"
TARGET_PATH="$REPO_ROOT/.git/hooks/$HOOK_NAME"

if [[ ! -f "$SAMPLE_PATH" ]]; then
  echo "[setup_hooks] Sample hook not found: $SAMPLE_PATH" >&2
  exit 1
fi

if [[ -e "$TARGET_PATH" && "$FORCE" != true ]]; then
  echo "[setup_hooks] $HOOK_NAME already exists at .git/hooks/. Use --force to overwrite." >&2
  exit 1
fi

cp "$SAMPLE_PATH" "$TARGET_PATH"
chmod +x "$TARGET_PATH"

echo "[setup_hooks] Installed $HOOK_NAME hook from $SAMPLE_PATH"
