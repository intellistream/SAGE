#!/usr/bin/env bash
set -euo pipefail

# Deferred real-online comparison for the Semantic MapReduce reducer contract.
# This script does not start vLLM-HUST and does not reserve an NPU by itself.
# Start the NPU3 endpoint separately through external/vllm-hust-dev-hub/manage.sh,
# then opt in with ALLOW_NPU3_REAL_ONLINE=1.

if [[ "${ALLOW_NPU3_REAL_ONLINE:-0}" != "1" ]]; then
  echo "Refusing to run. Set ALLOW_NPU3_REAL_ONLINE=1 after NPU3 is free." >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

EVENTS="${EVENTS:-20000}"
SHARDS="${SHARDS:-8}"
TOP_K="${TOP_K:-16}"
SEED="${SEED:-7}"
MAP_POLICY="${MAP_POLICY:-tail-aware}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-npu3-llm-reducer-comparison}"
OUTDIR="${OUTDIR:-.sage/benchmarks/real_online_semantic_mapreduce/${RUN_ID}}"

BASE_URL="${SAGE_LSA_LLM_BASE_URL:-http://127.0.0.1:18383}"
MODEL="${SAGE_LSA_LLM_MODEL:-qwen3-32b}"
API_KEY_ENV="${SAGE_LSA_LLM_API_KEY_ENV:-VLLM_HUST_API_KEY}"
ENV_FILE="${SAGE_LSA_LLM_ENV_FILE:-$REPO_ROOT/external/vllm-hust-dev-hub/.env}"
ENDPOINT_TYPE="${SAGE_LSA_LLM_ENDPOINT_TYPE:-chat}"
CONDA_ENV="${SAGE_LSA_CONDA_ENV:-esage-vllm-hust-dev}"
LLM_MAX_EVIDENCE="${SAGE_LSA_LLM_MAX_EVIDENCE:-24}"
LLM_MAX_TOKENS="${SAGE_LSA_LLM_MAX_TOKENS:-768}"
LLM_TIMEOUT_SEC="${SAGE_LSA_LLM_TIMEOUT_SEC:-240}"

mkdir -p "$OUTDIR"

health_url="${BASE_URL%/}/health"
if ! curl -fsS --max-time 5 "$health_url" >/dev/null; then
  echo "Endpoint health check failed: $health_url" >&2
  echo "Start the service through external/vllm-hust-dev-hub/manage.sh on NPU3 first." >&2
  exit 3
fi

repo_dirty=false
if [[ -n "$(git status --short)" ]]; then
  repo_dirty=true
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
for name in ("sage", "vllm", "torch", "torch-npu", "numpy", "ray", "langgraph", "llama-index-core"):
    try:
        packages[name] = metadata.version(name)
    except metadata.PackageNotFoundError:
        packages[name] = None
print(json.dumps({"python": sys.executable, "version": sys.version, "packages": packages}, indent=2))
'
}

{
  echo "run_id=$RUN_ID"
  echo "repo_commit=$(git rev-parse HEAD)"
  echo "repo_dirty=$repo_dirty"
  echo "conda_env=$CONDA_ENV"
  echo "events=$EVENTS"
  echo "shards=$SHARDS"
  echo "top_k=$TOP_K"
  echo "seed=$SEED"
  echo "map_policy=$MAP_POLICY"
  echo "base_url=$BASE_URL"
  echo "model=$MODEL"
  echo "endpoint_type=$ENDPOINT_TYPE"
  echo "llm_max_evidence=$LLM_MAX_EVIDENCE"
  echo "llm_max_tokens=$LLM_MAX_TOKENS"
  echo "llm_timeout_sec=$LLM_TIMEOUT_SEC"
  git submodule status --recursive || true
} > "$OUTDIR/manifest.txt"
record_python_env > "$OUTDIR/python-env.json"

RUN_ID="$RUN_ID" \
CONDA_ENV="$CONDA_ENV" \
BASE_URL="$BASE_URL" \
MODEL="$MODEL" \
ENDPOINT_TYPE="$ENDPOINT_TYPE" \
EVENTS="$EVENTS" \
SHARDS="$SHARDS" \
TOP_K="$TOP_K" \
SEED="$SEED" \
MAP_POLICY="$MAP_POLICY" \
LLM_MAX_EVIDENCE="$LLM_MAX_EVIDENCE" \
LLM_MAX_TOKENS="$LLM_MAX_TOKENS" \
LLM_TIMEOUT_SEC="$LLM_TIMEOUT_SEC" \
  python - "$OUTDIR" "$0" <<'PY'
import json
import os
import subprocess
import sys
import time
from pathlib import Path

outdir = Path(sys.argv[1])
entrypoint = sys.argv[2]
root = Path.cwd()

def git(path: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"

def submodule(path: str) -> dict:
    module = root / path
    if not module.exists():
        return {"path": path, "present": False}
    return {
        "path": path,
        "present": True,
        "commit": git(module, "rev-parse", "HEAD"),
        "branch": git(module, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git(module, "status", "--porcelain")),
    }

metadata = {
    "run_id": os.environ.get("RUN_ID", ""),
    "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "evidence_label": "real-online",
    "entrypoint": entrypoint,
    "parent_repo": {
        "path": str(root),
        "commit": git(root, "rev-parse", "HEAD"),
        "branch": git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git(root, "status", "--porcelain")),
    },
    "conda_env": os.environ.get("CONDA_ENV", os.environ.get("SAGE_LSA_CONDA_ENV", "")),
    "endpoint": {
        "base_url": os.environ.get("BASE_URL", os.environ.get("SAGE_LSA_LLM_BASE_URL", "")),
        "model": os.environ.get("MODEL", os.environ.get("SAGE_LSA_LLM_MODEL", "")),
        "endpoint_type": os.environ.get("ENDPOINT_TYPE", os.environ.get("SAGE_LSA_LLM_ENDPOINT_TYPE", "")),
    },
    "workload_source": {
        "kind": "repo-local",
        "path": "src/sage/workloads/large_scale_analysis.py",
        "suite": "large_scale_analysis",
    },
    "shared_workload_submodule": submodule("third_party/llm-serving-workloads"),
    "runtime_submodules": {
        path: submodule(path)
        for path in (
            "external/vllm-hust",
            "external/vllm-ascend-hust",
            "external/triton-ascend-hust",
            "external/vllm-hust-dev-hub",
            "third_party/ascend-runtime-manager",
        )
    },
    "parameters": {
        "events": os.environ.get("EVENTS", ""),
        "shards": os.environ.get("SHARDS", ""),
        "top_k": os.environ.get("TOP_K", ""),
        "seed": os.environ.get("SEED", ""),
        "map_policy": os.environ.get("MAP_POLICY", ""),
        "llm_max_evidence": os.environ.get("LLM_MAX_EVIDENCE", ""),
        "llm_max_tokens": os.environ.get("LLM_MAX_TOKENS", ""),
        "llm_timeout_sec": os.environ.get("LLM_TIMEOUT_SEC", ""),
    },
}
(outdir / "run_metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

run_one() {
  local reducer="$1"
  local output="$OUTDIR/${reducer}.json"
  run_python python tools/benchmark_carrier/run_large_scale_analysis_workload.py \
    --events "$EVENTS" \
    --shards "$SHARDS" \
    --seed "$SEED" \
    --top-k "$TOP_K" \
    --map-policy "$MAP_POLICY" \
    --reducer "$reducer" \
    --llm-base-url "$BASE_URL" \
    --llm-model "$MODEL" \
    --llm-api-key-env "$API_KEY_ENV" \
    --llm-env-file "$ENV_FILE" \
    --llm-endpoint-type "$ENDPOINT_TYPE" \
    --llm-max-evidence "$LLM_MAX_EVIDENCE" \
    --llm-max-tokens "$LLM_MAX_TOKENS" \
    --llm-timeout-sec "$LLM_TIMEOUT_SEC" \
    --llm-structured-output \
    --output "$output"
}

run_one deterministic
run_one llm-openai

run_python python - "$OUTDIR" <<'PY'
import json
import sys
from pathlib import Path

outdir = Path(sys.argv[1])
rows = []
for reducer in ("deterministic", "llm-openai"):
    payload = json.loads((outdir / f"{reducer}.json").read_text())
    cost = payload.get("cost_accounting", {})
    rows.append(
        {
            "reducer": reducer,
            "precision": payload["precision"],
            "recall": payload["recall"],
            "f1": payload["f1"],
            "semantic_reduce_ms": payload["operator_duration_ms"]["SemanticReduce"],
            "total_tokens": cost.get("total_tokens", 0),
            "estimated_cost_usd": cost.get("estimated_cost_usd", 0.0),
            "missed_incident_ids": [
                item["incident_id"] for item in payload.get("missed_incidents", [])
            ],
        }
    )
(outdir / "comparison_summary.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(rows, ensure_ascii=False, indent=2))
PY

echo "RESULT_DIR=$OUTDIR"
