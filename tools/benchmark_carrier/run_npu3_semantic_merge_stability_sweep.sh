#!/usr/bin/env bash
set -euo pipefail

# Clean real-online repeated-sampling and candidate-budget sweep. This wrapper
# never reads or prints the API key; the inner runner resolves only the named
# environment variable through the repo-owned untracked env file.

if [[ "${ALLOW_NPU3_REAL_ONLINE:-0}" != "1" ]]; then
  echo "Refusing to run. Set ALLOW_NPU3_REAL_ONLINE=1 after NPU3 preflight." >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

BUDGETS="${SAGE_SMR_CANDIDATE_BUDGETS:-4,8,12}"
SAMPLES="${SAGE_SMR_SAMPLES:-5}"
SWEEP_ID="${SAGE_SMR_SWEEP_ID:-$(date -u +%Y%m%dT%H%M%SZ)-eurosys27-stability}"
SWEEP_ROOT="${SAGE_SMR_SWEEP_ROOT:-.sage/benchmarks/real_online_semantic_merge_stability/$SWEEP_ID}"
CONDA_EXE="${SAGE_SMR_CONDA_EXE:-/home/shuhao/miniconda3/bin/conda}"
CONDA_ENV="${SAGE_SMR_CONDA_ENV:-esage-vllm-hust-dev}"

[[ -z "$(git status --porcelain)" ]] || {
  echo "Clean-tree stability sweep requires a clean parent repository." >&2
  exit 2
}
[[ ! -e "$SWEEP_ROOT" ]] || {
  echo "Refusing to overwrite sweep output: $SWEEP_ROOT" >&2
  exit 2
}
mkdir -p "$SWEEP_ROOT"

IFS=',' read -r -a budget_values <<< "$BUDGETS"
run_dirs=()
for raw_budget in "${budget_values[@]}"; do
  budget="${raw_budget//[[:space:]]/}"
  [[ "$budget" =~ ^[1-9][0-9]*$ ]] || {
    echo "Invalid candidate budget: $raw_budget" >&2
    exit 2
  }
  run_id="${SWEEP_ID}-candidates${budget}"
  outdir="$SWEEP_ROOT/candidates-$budget"
  run_dirs+=("$outdir")
  if ! ALLOW_NPU3_REAL_ONLINE=1 \
    SAGE_SMR_SAMPLES="$SAMPLES" \
    SAGE_SMR_LLM_MAX_CANDIDATES="$budget" \
    SEEDS=7,11,13 \
    SCENARIOS=single-service,cascade,shared-bottleneck,concurrent,false-correlation,partial-evidence,ambiguous-disconnected-merge,ambiguous-temporal-split,ambiguous-overmerge \
    REDUCERS=hybrid-hint,llm-pairwise-validated,llm-pairwise-action-validated \
    RUN_ID="$run_id" \
    OUTDIR="$outdir" \
    tools/benchmark_carrier/run_npu3_semantic_merge_llm_comparison.sh; then
    printf 'Run failed for candidate budget %s. Partial output is diagnostic only.\n' \
      "$budget" > "$SWEEP_ROOT/candidates-$budget.FAILED.txt"
    exit 1
  fi
  "$CONDA_EXE" run --no-capture-output -n "$CONDA_ENV" env PYTHONPATH=src \
    python tools/benchmark_carrier/verify_semantic_merge_artifact.py \
    "$outdir" \
    --endpoint-metadata "$SAGE_SMR_ENDPOINT_METADATA" \
    --profile full \
    --min-samples "$SAMPLES" \
    --output "$outdir/artifact_gate.json"
done

"$CONDA_EXE" run --no-capture-output -n "$CONDA_ENV" env PYTHONPATH=src \
  python tools/benchmark_carrier/summarize_semantic_merge_budget_sweep.py \
  "${run_dirs[@]}" --output "$SWEEP_ROOT/quality_latency_token_curve.json"

printf 'RESULT_DIR=%s\n' "$SWEEP_ROOT"
