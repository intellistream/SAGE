#!/usr/bin/env bash
set -euo pipefail

# Real-online comparison for the Semantic MapReduce semantic-merge suite.
# This script does not start vLLM-HUST and does not reserve an NPU by itself.
# Start the NPU3 endpoint through external/vllm-hust-dev-hub/manage.sh, then
# opt in with ALLOW_NPU3_REAL_ONLINE=1.

if [[ "${ALLOW_NPU3_REAL_ONLINE:-0}" != "1" ]]; then
  echo "Refusing to run. Set ALLOW_NPU3_REAL_ONLINE=1 after NPU3 is free." >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SEEDS="${SEEDS:-7,11,13}"
SCENARIOS="${SCENARIOS:-partial-evidence,false-correlation,concurrent}"
REDUCERS="${REDUCERS:-semantic-graph,hybrid-hint,llm-hybrid,llm-hybrid-validated,llm-openai}"
SHARDS="${SHARDS:-8}"
INCIDENTS="${INCIDENTS:-4}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-npu3-semantic-merge-llm-comparison}"
OUTDIR="${OUTDIR:-.sage/benchmarks/real_online_semantic_merge/${RUN_ID}}"

BASE_URL="${SAGE_SMR_LLM_BASE_URL:-http://127.0.0.1:18383}"
MODEL="${SAGE_SMR_LLM_MODEL:-qwen3-32b}"
API_KEY_ENV="${SAGE_SMR_LLM_API_KEY_ENV:-VLLM_HUST_API_KEY}"
ENV_FILE="${SAGE_SMR_LLM_ENV_FILE:-$REPO_ROOT/external/vllm-hust-dev-hub/.env}"
CONDA_ENV="${SAGE_SMR_CONDA_ENV:-esage-vllm-hust-dev}"
LLM_MAX_EVIDENCE="${SAGE_SMR_LLM_MAX_EVIDENCE:-24}"
LLM_MAX_CANDIDATES="${SAGE_SMR_LLM_MAX_CANDIDATES:-12}"
LLM_MAX_TOKENS="${SAGE_SMR_LLM_MAX_TOKENS:-384}"
LLM_TIMEOUT_SEC="${SAGE_SMR_LLM_TIMEOUT_SEC:-240}"

mkdir -p "$OUTDIR"

export RUN_ID OUTDIR BASE_URL MODEL API_KEY_ENV CONDA_ENV
export SEEDS SCENARIOS REDUCERS SHARDS INCIDENTS
export LLM_MAX_EVIDENCE LLM_MAX_CANDIDATES LLM_MAX_TOKENS LLM_TIMEOUT_SEC

health_url="${BASE_URL%/}/health"
if ! curl -fsS --max-time 5 "$health_url" >/dev/null; then
  echo "Endpoint health check failed: $health_url" >&2
  echo "Start the service through external/vllm-hust-dev-hub/manage.sh on NPU3 first." >&2
  exit 3
fi

run_python() {
  if [[ -n "$CONDA_ENV" ]]; then
    conda run -n "$CONDA_ENV" env PYTHONPATH=src "$@"
  else
    env PYTHONPATH=src "$@"
  fi
}

record_python_env() {
  run_python python -c '
import importlib.metadata as metadata
import json
import sys
packages = {}
for name in ("sage", "vllm", "torch", "torch-npu", "numpy"):
    try:
        packages[name] = metadata.version(name)
    except metadata.PackageNotFoundError:
        packages[name] = None
print(json.dumps({"python": sys.executable, "version": sys.version, "packages": packages}, indent=2))
'
}

{
  echo "run_id=$RUN_ID"
  echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo_commit=$(git rev-parse HEAD)"
  echo "repo_branch=$(git rev-parse --abbrev-ref HEAD)"
  echo "repo_dirty=$([[ -n "$(git status --short)" ]] && echo true || echo false)"
  echo "conda_env=$CONDA_ENV"
  echo "scenarios=$SCENARIOS"
  echo "seeds=$SEEDS"
  echo "reducers=$REDUCERS"
  echo "shards=$SHARDS"
  echo "incidents=$INCIDENTS"
  echo "base_url=$BASE_URL"
  echo "model=$MODEL"
  echo "llm_max_evidence=$LLM_MAX_EVIDENCE"
  echo "llm_max_candidates=$LLM_MAX_CANDIDATES"
  echo "llm_max_tokens=$LLM_MAX_TOKENS"
  echo "llm_timeout_sec=$LLM_TIMEOUT_SEC"
  git submodule status --recursive || true
} > "$OUTDIR/manifest.txt"
record_python_env > "$OUTDIR/python-env.json"

python - "$OUTDIR/run_metadata.json" <<'PY'
import json
import os
import subprocess
import sys
import time


def git_output(args):
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return "unknown"


def submodule_status(path):
    if not os.path.exists(path):
        return {"path": path, "present": False}
    def module_git(args):
        try:
            return subprocess.check_output(["git", "-C", path, *args], text=True).strip()
        except Exception:
            return "unknown"
    return {
        "path": path,
        "present": True,
        "commit": module_git(["rev-parse", "HEAD"]),
        "branch": module_git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(module_git(["status", "--porcelain"])),
    }


metadata = {
    "run_id": os.environ.get("RUN_ID", ""),
    "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "evidence_label": "real-online",
    "conda_env": os.environ.get("CONDA_ENV", ""),
    "endpoint": {
        "base_url": os.environ.get("BASE_URL", ""),
        "model": os.environ.get("MODEL", ""),
        "api_key_env": os.environ.get("API_KEY_ENV", ""),
    },
    "llm_reducer": {
        "max_evidence": int(os.environ.get("LLM_MAX_EVIDENCE", "0") or "0"),
        "max_candidates": int(os.environ.get("LLM_MAX_CANDIDATES", "0") or "0"),
        "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "0") or "0"),
        "timeout_sec": int(os.environ.get("LLM_TIMEOUT_SEC", "0") or "0"),
        "structured_output": True,
    },
    "workload": {
        "source": "repo-local",
        "path": "src/sage/workloads/semantic_merge_analysis.py",
        "seeds": os.environ.get("SEEDS", ""),
        "scenarios": os.environ.get("SCENARIOS", ""),
        "reducers": os.environ.get("REDUCERS", ""),
        "shards": int(os.environ.get("SHARDS", "0") or "0"),
        "incidents": int(os.environ.get("INCIDENTS", "0") or "0"),
    },
    "git": {
        "commit": git_output(["rev-parse", "HEAD"]),
        "branch": git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(git_output(["status", "--porcelain"])),
    },
    "shared_workload_submodule": submodule_status("third_party/llm-serving-workloads"),
    "runtime_submodules": {
        path: submodule_status(path)
        for path in (
            "external/vllm-hust",
            "external/vllm-ascend-hust",
            "external/triton-ascend-hust",
            "external/vllm-hust-dev-hub",
            "third_party/ascend-runtime-manager",
        )
    },
}
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(metadata, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
PY

export SAGE_SMR_LLM_BASE_URL="$BASE_URL"
export SAGE_SMR_LLM_MODEL="$MODEL"
export SAGE_SMR_LLM_API_KEY_ENV="$API_KEY_ENV"
export SAGE_SMR_LLM_ENV_FILE="$ENV_FILE"
export SAGE_SMR_LLM_MAX_EVIDENCE="$LLM_MAX_EVIDENCE"
export SAGE_SMR_LLM_MAX_CANDIDATES="$LLM_MAX_CANDIDATES"
export SAGE_SMR_LLM_MAX_TOKENS="$LLM_MAX_TOKENS"
export SAGE_SMR_LLM_TIMEOUT_SEC="$LLM_TIMEOUT_SEC"
export SAGE_SMR_LLM_STRUCTURED_OUTPUT="${SAGE_SMR_LLM_STRUCTURED_OUTPUT:-1}"

run_python python tools/benchmark_carrier/run_semantic_merge_matrix.py \
  --seeds "$SEEDS" \
  --scenarios "$SCENARIOS" \
  --reducers "$REDUCERS" \
  --shards "$SHARDS" \
  --incidents "$INCIDENTS" \
  --output-root "$OUTDIR" \
  --run-id matrix

python - "$OUTDIR/matrix/manifest.json" "$OUTDIR/run_metadata.json" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
metadata_path = Path(sys.argv[2])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
manifest["evidence_label"] = "real-online"
manifest["real_online"] = metadata
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

run_python python tools/benchmark_carrier/summarize_semantic_merge_llm_comparison.py \
  "$OUTDIR/matrix" \
  --output "$OUTDIR/comparison_summary.json"

echo "RESULT_DIR=$OUTDIR"
