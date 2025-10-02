#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./tools/maintenance/prepare_branch_checkout.sh <target-branch>

Safely switch the SAGE repository to another branch by pruning submodules
that are absent on the target branch before running "git checkout".

Steps performed:
  1. Compare the current branch's .gitmodules with the target branch.
  2. Deinit and remove submodule working trees that would block checkout.
  3. Checkout the target branch.
  4. Invoke manage_submodule_branches.sh switch to align submodules.
EOF
}

ensure_repo_root() {
  if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "[prepare_checkout] Not inside a Git repository" >&2
    exit 1
  fi
}

list_submodules_from_file() {
  local file_path="$1"
  if [[ -f "$file_path" ]]; then
    git config --file "$file_path" --get-regexp path 2>/dev/null | awk '{print $2}'
  fi
}

list_current_submodules() {
  if [[ -f .gitmodules ]]; then
    list_submodules_from_file .gitmodules
  fi
}

list_target_submodules() {
  local target="$1"
  local tmp
  tmp=$(mktemp)
  if git show "${target}:.gitmodules" >"$tmp" 2>/dev/null; then
    list_submodules_from_file "$tmp"
  fi
  rm -f "$tmp"
}

cleanup_submodule_path() {
  local path="$1"
  echo "[prepare_checkout] Removing submodule path: $path"
  git submodule deinit -f -- "$path" >/dev/null 2>&1 || true
  rm -rf "$path"
}

main() {
  if [[ $# -eq 0 ]]; then
    usage
    exit 1
  fi

  if [[ $1 == "-h" || $1 == "--help" ]]; then
    usage
    exit 0
  fi

  local target_branch="$1"
  ensure_repo_root

  if ! git show-ref --verify --quiet "refs/heads/${target_branch}" && \
     ! git show-ref --verify --quiet "refs/remotes/origin/${target_branch}"; then
    echo "[prepare_checkout] Branch '${target_branch}' not found (local or remote)" >&2
    exit 1
  fi

  local current_branch
  current_branch=$(git rev-parse --abbrev-ref HEAD)
  if [[ "$current_branch" == "$target_branch" ]]; then
    echo "[prepare_checkout] Already on branch '${target_branch}'"
    exit 0
  fi

  mapfile -t current_paths < <(list_current_submodules)
  mapfile -t target_paths < <(list_target_submodules "$target_branch")

  declare -A target_set=()
  for path in "${target_paths[@]}"; do
    target_set["$path"]=1
  done

  for path in "${current_paths[@]}"; do
    if [[ -z "${target_set[$path]:-}" ]]; then
      if [[ -e "$path" ]]; then
        cleanup_submodule_path "$path"
      fi
    fi
  done

  echo "[prepare_checkout] Checking out ${target_branch}"
  git checkout "$target_branch"

  local switch_script="$(git rev-parse --show-toplevel)/tools/maintenance/manage_submodule_branches.sh"
  if [[ -x "$switch_script" ]]; then
    "$switch_script" switch
  else
    echo "[prepare_checkout] Warning: manage_submodule_branches.sh not found or not executable" >&2
  fi
}

main "$@"
