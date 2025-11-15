#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./tools/maintenance/setup_hooks.sh [options]

Install tracked Git hook samples into the local .git/hooks directory.

Options:
  -h, --help          Show this help message and exit
  --hook NAME         Hook filename to install (default: all)
  -f, --force         Overwrite existing hook file if present
  --all               Install all available hooks (default)

Available hooks:
  - post-checkout: Automatically sync submodule branches
  - post-submodule-update: Generate SUBMODULE.md markers
EOF
}

HOOK_NAME="all"
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
    --all)
      HOOK_NAME="all"
      shift
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

# Function to install a single hook
install_hook() {
  local hook_name="$1"
  local sample_path="$REPO_ROOT/tools/maintenance/git-hooks/$hook_name"
  local target_path="$REPO_ROOT/.git/hooks/$hook_name"

  if [[ ! -f "$sample_path" ]]; then
    echo "[setup_hooks] Sample hook not found: $sample_path" >&2
    return 1
  fi

  if [[ -e "$target_path" && "$FORCE" != true ]]; then
    echo "[setup_hooks] $hook_name already exists. Use --force to overwrite." >&2
    return 1
  fi

  cp "$sample_path" "$target_path"
  chmod +x "$target_path"
  echo "[setup_hooks] ✅ Installed $hook_name"
  return 0
}

# Install hooks based on HOOK_NAME
if [[ "$HOOK_NAME" == "all" ]]; then
  # Install all available hooks
  hooks_installed=0
  for hook_file in "$REPO_ROOT/tools/maintenance/git-hooks/"*; do
    if [[ -f "$hook_file" ]]; then
      hook_name=$(basename "$hook_file")
      if install_hook "$hook_name"; then
        hooks_installed=$((hooks_installed + 1))
      fi
    fi
  done

  if [[ $hooks_installed -gt 0 ]]; then
    echo "[setup_hooks] Installed $hooks_installed hook(s)"
  else
    echo "[setup_hooks] No hooks were installed"
  fi
else
  # Install specific hook
  install_hook "$HOOK_NAME"
fi
