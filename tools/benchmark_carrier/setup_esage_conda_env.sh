#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  tools/benchmark_carrier/setup_esage_conda_env.sh [--source-env ENV] [--target-env ENV] [--dev-hub PATH] [--prepare-source-env] [--with-adapter-comparison]

Create an eSAGE experiment environment by cloning the vLLM-HUST development
conda environment, then installing the SAGE dependencies needed by the
benchmark carrier and workload tests.

Defaults:
  --source-env vllm-hust-dev
  --target-env esage-vllm-hust-dev
  --dev-hub   $HOME/vllm-hust-dev-hub

The script also accepts "vllmhustdev" as a source-env alias when an environment
with that exact name exists.

When --prepare-source-env is set, this script first delegates vLLM-HUST source
environment preparation to vllm-hust-dev-hub:

  bash <dev-hub>/scripts/quickstart.sh --conda --install --install-mode refresh --install-scope core --env-name <source-env> -y
EOF
}

SOURCE_ENV="${ESAGE_SOURCE_ENV:-vllm-hust-dev}"
TARGET_ENV="${ESAGE_TARGET_ENV:-esage-vllm-hust-dev}"
DEV_HUB="${ESAGE_VLLM_HUST_DEV_HUB:-$HOME/vllm-hust-dev-hub}"
PREPARE_SOURCE_ENV=0
WITH_ADAPTER_COMPARISON=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source-env)
      SOURCE_ENV="${2:?missing value for --source-env}"
      shift 2
      ;;
    --target-env)
      TARGET_ENV="${2:?missing value for --target-env}"
      shift 2
      ;;
    --dev-hub)
      DEV_HUB="${2:?missing value for --dev-hub}"
      shift 2
      ;;
    --prepare-source-env)
      PREPARE_SOURCE_ENV=1
      shift
      ;;
    --with-adapter-comparison)
      WITH_ADAPTER_COMPARISON=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v conda >/dev/null 2>&1; then
  echo "conda is required but was not found in PATH." >&2
  exit 1
fi

env_exists() {
  local env_name="$1"
  conda env list | awk '{print $1}' | grep -Fxq "$env_name"
}

prepare_source_env_with_dev_hub() {
  local quickstart="$DEV_HUB/scripts/quickstart.sh"
  if [ ! -x "$quickstart" ]; then
    echo "vllm-hust-dev-hub quickstart script was not found or is not executable: $quickstart" >&2
    echo "Set --dev-hub PATH or ESAGE_VLLM_HUST_DEV_HUB to the vllm-hust-dev-hub checkout." >&2
    exit 1
  fi
  echo "Preparing vLLM-HUST source env '$SOURCE_ENV' via vllm-hust-dev-hub..."
  (
    cd "$DEV_HUB"
    bash scripts/quickstart.sh \
      --conda \
      --install \
      --install-mode refresh \
      --install-scope core \
      --env-name "$SOURCE_ENV" \
      -y
  )
}

if [ "$PREPARE_SOURCE_ENV" -eq 1 ]; then
  prepare_source_env_with_dev_hub
fi

if ! env_exists "$SOURCE_ENV"; then
  if [ "$SOURCE_ENV" = "vllm-hust-dev" ] && env_exists "vllmhustdev"; then
    SOURCE_ENV="vllmhustdev"
  else
    echo "Source conda env '$SOURCE_ENV' was not found." >&2
    echo "If this machine uses vllm-hust-dev-hub, rerun with --prepare-source-env." >&2
    echo "Available envs:" >&2
    conda env list >&2
    exit 1
  fi
fi

if env_exists "$TARGET_ENV"; then
  echo "Target conda env '$TARGET_ENV' already exists; reusing it."
else
  echo "Cloning conda env '$SOURCE_ENV' -> '$TARGET_ENV'..."
  conda create -y -n "$TARGET_ENV" --clone "$SOURCE_ENV"
fi

TARGET_PREFIX="$(conda env list | awk -v env="$TARGET_ENV" '$1 == env {print $NF}')"
if [ -z "$TARGET_PREFIX" ] || [ ! -d "$TARGET_PREFIX" ]; then
  echo "Could not resolve prefix for target env '$TARGET_ENV'." >&2
  exit 1
fi

patch_strict_ascend_hook() {
  local hook_path="$TARGET_PREFIX/etc/conda/activate.d/hust-ascend-manager.sh"
  if [ ! -f "$hook_path" ]; then
    return 0
  fi
  if grep -q "esage tolerant hook patch" "$hook_path"; then
    return 0
  fi
  python - "$hook_path" "$TARGET_PREFIX" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
target_prefix = sys.argv[2]
text = path.read_text(encoding="utf-8")
pattern = re.compile(
    r'_hust_ascend_manager_exports="\$\((?P<python>[^"]+/bin/python) '
    r'-m hust_ascend_manager\.cli env --shell\)" \|\| return \$\?\n'
    r'eval "\$\{_hust_ascend_manager_exports\}"\n'
    r'unset _hust_ascend_manager_exports\n'
    r'unset _hust_ascend_manager_hook_level\n'
)
match = pattern.search(text)
if not match:
    raise SystemExit("strict hust-ascend-manager hook shape was not recognized")
python_bin = match.group("python")
expected_python = f"{target_prefix}/bin/python"
if python_bin != expected_python:
    raise SystemExit(
        f"unexpected hook python path {python_bin!r}; expected {expected_python!r}"
    )
new = f'''# esage tolerant hook patch: cloned benchmark environments may be used on
# login/build hosts where the Ascend runtime root is intentionally unavailable.
_hust_ascend_manager_exports="$({python_bin} -m hust_ascend_manager.cli env --shell 2>/dev/null || true)"
if [[ -n "${{_hust_ascend_manager_exports}}" ]]; then
  eval "${{_hust_ascend_manager_exports}}"
fi
unset _hust_ascend_manager_exports
unset _hust_ascend_manager_hook_level
'''
path.write_text(pattern.sub(new, text), encoding="utf-8")
PY
  echo "Patched strict Ascend activation hook in '$TARGET_ENV' to be tolerant."
}

patch_strict_ascend_hook

echo "Checking Python version in '$TARGET_ENV'..."
conda run -n "$TARGET_ENV" python -c \
  'import sys; print(sys.version); raise SystemExit(0 if sys.version_info >= (3, 11) else "SAGE requires Python >= 3.11; use a vLLM-HUST dev env with Python 3.11+ as the source.")'

echo "Installing SAGE experiment dependencies into '$TARGET_ENV'..."
conda run -n "$TARGET_ENV" python -m pip install --upgrade pip
SAGE_EXTRAS="serving-edge"
if [ "$WITH_ADAPTER_COMPARISON" -eq 1 ]; then
  SAGE_EXTRAS="${SAGE_EXTRAS},adapter-comparison"
fi
conda run -n "$TARGET_ENV" python -m pip install -e ".[${SAGE_EXTRAS}]"

# Install the experiment/test tooling explicitly instead of using the full
# `dev` extra, which includes repository publishing helpers that may not be
# available from the configured package index on benchmark machines.
conda run -n "$TARGET_ENV" python -m pip install \
  'pytest>=7.4.0' \
  'pytest-cov>=4.0.0' \
  'pytest-asyncio>=0.21.0' \
  'pytest-mock>=3.12.0' \
  'ruff>=0.15.0' \
  'mypy>=1.7.0' \
  'pre-commit>=3.5.0' \
  'aiohttp>=3.9,<4'

echo "Verifying eSAGE workload dependencies..."
conda run -n "$TARGET_ENV" python -c \
  'import importlib; [importlib.import_module(module) for module in ("sage", "cloudpickle", "yaml", "fastapi", "aiohttp")]; print("SAGE/eSAGE dependency import check passed.")'

if [ "$WITH_ADAPTER_COMPARISON" -eq 1 ]; then
  conda run -n "$TARGET_ENV" python -c \
    'import importlib; [importlib.import_module(module) for module in ("ray", "langgraph", "llama_index.core")]; print("Adapter comparison dependency import check passed.")'
fi

if ! conda run -n "$TARGET_ENV" python -c \
  'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("vllm") else 1)' >/dev/null 2>&1; then
  echo "Warning: Python module 'vllm' is not importable in '$TARGET_ENV'."
  echo "Synthetic SAGE workloads do not require it, but real replay experiments"
  echo "using openai_replay_carrier.py need vLLM benchmark helpers available via"
  echo "the cloned source env, an editable vLLM-HUST install, or PYTHONPATH."
  echo "On vLLM-HUST machines, prefer preparing the source env through"
  echo "vllm-hust-dev-hub: rerun this script with --prepare-source-env."
fi

echo
echo "Environment ready: $TARGET_ENV"
echo "Run examples:"
echo "  conda run -n $TARGET_ENV env PYTHONPATH=src python -m pytest -q src/tests/test_large_scale_analysis_workload.py"
echo "  conda run -n $TARGET_ENV env PYTHONPATH=src python tools/benchmark_carrier/run_large_scale_analysis_workload.py --events 50000 --shards 16 --seed 7 --top-k 12"
