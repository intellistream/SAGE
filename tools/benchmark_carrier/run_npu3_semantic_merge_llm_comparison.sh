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

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

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
CONDA_EXE="${SAGE_SMR_CONDA_EXE:-/home/shuhao/miniconda3/bin/conda}"
NPU_DEVICE="${SAGE_SMR_NPU_DEVICE:-3}"
ENDPOINT_METADATA="${SAGE_SMR_ENDPOINT_METADATA:-}"
PREFLIGHT_ONLY="${SAGE_SMR_PREFLIGHT_ONLY:-0}"
LLM_MAX_EVIDENCE="${SAGE_SMR_LLM_MAX_EVIDENCE:-24}"
LLM_MAX_CANDIDATES="${SAGE_SMR_LLM_MAX_CANDIDATES:-12}"
LLM_MAX_TOKENS="${SAGE_SMR_LLM_MAX_TOKENS:-384}"
LLM_TIMEOUT_SEC="${SAGE_SMR_LLM_TIMEOUT_SEC:-240}"

export RUN_ID OUTDIR BASE_URL MODEL API_KEY_ENV CONDA_ENV
export NPU_DEVICE ENDPOINT_METADATA
export SEEDS SCENARIOS REDUCERS SHARDS INCIDENTS
export LLM_MAX_EVIDENCE LLM_MAX_CANDIDATES LLM_MAX_TOKENS LLM_TIMEOUT_SEC

run_python() {
  "$CONDA_EXE" run --no-capture-output -n "$CONDA_ENV" env PYTHONPATH=src "$@"
}

[[ "$NPU_DEVICE" == "3" ]] || die "Refusing non-NPU3 comparison: $NPU_DEVICE"
[[ "$CONDA_ENV" == "esage-vllm-hust-dev" ]] \
  || die "Expected dedicated environment esage-vllm-hust-dev, got $CONDA_ENV"
[[ -x "$CONDA_EXE" ]] || die "Conda executable not found: $CONDA_EXE"
[[ -n "$ENDPOINT_METADATA" && -f "$ENDPOINT_METADATA" ]] \
  || die "Set SAGE_SMR_ENDPOINT_METADATA to the controlled endpoint metadata.json"
[[ ! -e "$OUTDIR" ]] || die "Output directory already exists: $OUTDIR"
[[ -z "$(git status --porcelain)" ]] \
  || die "Parent repository is dirty; commit or otherwise preserve scoped changes first."

required_submodules=(
  external/vllm-hust
  external/vllm-ascend-hust
  external/triton-ascend-hust
  external/vllm-hust-dev-hub
  third_party/ascend-runtime-manager
  third_party/llm-serving-workloads
)
for submodule in "${required_submodules[@]}"; do
  [[ -d "$submodule" && ! -L "$submodule" ]] \
    || die "Missing or symlinked repo-owned submodule: $submodule"
  [[ -z "$(git -C "$submodule" status --porcelain)" ]] \
    || die "Submodule is dirty: $submodule"
done

run_python python - "$ENDPOINT_METADATA" <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

path = Path(sys.argv[1])
metadata = json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


expected = {
    "evidence_label": "real-online",
    "base_url": os.environ["BASE_URL"],
    "npu_device": os.environ["NPU_DEVICE"],
    "served_model_name": os.environ["MODEL"],
    "conda_env": os.environ["CONDA_ENV"],
    "parent_repo_commit": git("rev-parse", "HEAD"),
    "parent_repo_dirty": False,
}
errors = []
for name, value in expected.items():
    actual = metadata.get(name)
    if name == "npu_device":
        actual = str(actual)
    if actual != value:
        errors.append(f"{name}: expected {value!r}, got {actual!r}")

recorded = metadata.get("submodules", {})
for submodule in (
    "external/vllm-hust",
    "external/vllm-ascend-hust",
    "external/triton-ascend-hust",
    "external/vllm-hust-dev-hub",
    "third_party/ascend-runtime-manager",
    "third_party/llm-serving-workloads",
):
    entry = recorded.get(submodule, {})
    current = subprocess.check_output(
        ["git", "-C", submodule, "rev-parse", "HEAD"], text=True
    ).strip()
    if entry.get("commit") != current or entry.get("dirty") is not False:
        errors.append(f"submodule provenance mismatch: {submodule}")

if errors:
    raise SystemExit("Endpoint provenance gate failed:\n- " + "\n- ".join(errors))
PY

health_url="${BASE_URL%/}/health"
if ! curl -fsS --max-time 5 "$health_url" >/dev/null; then
  die "Endpoint health check failed: $health_url"
fi

if [[ "$PREFLIGHT_ONLY" == "1" ]]; then
  echo "PREFLIGHT_OK endpoint=$BASE_URL model=$MODEL npu=$NPU_DEVICE env=$CONDA_ENV"
  exit 0
fi

mkdir -p "$OUTDIR"

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
  echo "npu_device=$NPU_DEVICE"
  echo "endpoint_metadata=$ENDPOINT_METADATA"
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

run_python python - "$OUTDIR/run_metadata.json" <<'PY'
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
    "hardware": {
        "npu_device": int(os.environ.get("NPU_DEVICE", "-1")),
        "device_label": f"NPU{os.environ.get('NPU_DEVICE', '')}",
    },
    "endpoint_provenance": os.environ.get("ENDPOINT_METADATA", ""),
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

run_python python - "$OUTDIR/matrix/manifest.json" "$OUTDIR/run_metadata.json" <<'PY'
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
