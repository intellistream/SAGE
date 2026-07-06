#!/usr/bin/env bash
set -euo pipefail

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEV_HUB="${SAGE_ROOT}/external/vllm-hust-dev-hub"
PREPARE_RUNTIME="${SAGE_ROOT}/tools/benchmark_carrier/prepare_vllm_ascend_runtime_branch.sh"

NPU_DEVICE="${SAGE_REAL_ONLINE_NPU_DEVICE:-3}"
PORT="${SAGE_REAL_ONLINE_PORT:-18383}"
MODEL_PATH="${SAGE_REAL_ONLINE_MODEL_PATH:-/data/shared_models/Qwen2.5-7B-Instruct}"
SERVED_MODEL_NAME="${SAGE_REAL_ONLINE_MODEL_NAME:-qwen25-7b-sage-realonline}"
CONDA_ENV="${SAGE_REAL_ONLINE_CONDA_ENV:-esage-vllm-hust-dev}"
SYSTEMD_UNIT="${SAGE_REAL_ONLINE_SYSTEMD_UNIT:-sage-smr-npu3.service}"
CONTAINER_NAME="${SAGE_REAL_ONLINE_CONTAINER:-sage-smr-npu${NPU_DEVICE}}"
HOST_WORKSPACE_ROOT="${SAGE_REAL_ONLINE_HOST_WORKSPACE_ROOT:-/home/shuhao}"
CONTAINER_WORKSPACE_ROOT="${SAGE_REAL_ONLINE_CONTAINER_WORKSPACE_ROOT:-/workspace}"
CONTAINER_WORKDIR="${SAGE_REAL_ONLINE_CONTAINER_WORKDIR:-/workspace/SAGE/external/vllm-hust-dev-hub}"
RUN_ID="${SAGE_REAL_ONLINE_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-npu${NPU_DEVICE}-semantic-mapreduce}"
OUTPUT_ROOT="${SAGE_REAL_ONLINE_OUTPUT_ROOT:-${SAGE_ROOT}/.sage/benchmarks/real_online_semantic_mapreduce/${RUN_ID}}"
EVENT_SIZES="${SAGE_REAL_ONLINE_EVENTS:-2000 20000}"
SHARD_COUNTS="${SAGE_REAL_ONLINE_SHARDS:-4 8}"
TOP_KS="${SAGE_REAL_ONLINE_TOP_KS:-8 12}"
SEED="${SAGE_REAL_ONLINE_SEED:-7}"

DRY_RUN=0
SKIP_SERVER_MANAGEMENT=0
KEEP_SERVER=0
SKIP_NPU_CHECK=0
SKIP_ONLINE_PROBE=0
SKIP_LLM_REDUCER=0
ALLOW_NEWER_RUNTIME=0

usage() {
  cat <<EOF
Usage:
  tools/benchmark_carrier/run_npu3_semantic_mapreduce_experiment.sh [options]

Run the real-online Semantic MapReduce experiment using only this SAGE checkout
and its feature-branch submodules. Defaults are intentionally conservative:
NPU 3, port 18383, dev-hub manage.sh, and SAGE-pinned runtime branches.

Options:
  --dry-run                  Print the resolved plan only.
  --skip-server-management   Reuse an already-running endpoint on --port.
  --keep-server              Leave a service started by this script running.
  --skip-npu-check           Do not require NPU 3 to be idle before launch.
  --skip-online-probe        Skip smoke and latency probes.
  --skip-llm-reducer         Only launch/probe the endpoint.
  --allow-newer-runtime      Allow submodules ahead of pinned commits.
  --npu DEVICE               Default: ${NPU_DEVICE}
  --port PORT                Default: ${PORT}
  --model-path PATH          Default: ${MODEL_PATH}
  --served-model NAME        Default: ${SERVED_MODEL_NAME}
  --conda-env NAME           Default: ${CONDA_ENV}
  --run-id ID                Default: ${RUN_ID}
  --output-root DIR          Default: ${OUTPUT_ROOT}
  --events "A B"             Default: "${EVENT_SIZES}"
  --shards "A B"             Default: "${SHARD_COUNTS}"
  --top-ks "A B"             Default: "${TOP_KS}"
  -h, --help                 Show this help.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --skip-server-management) SKIP_SERVER_MANAGEMENT=1; shift ;;
    --keep-server) KEEP_SERVER=1; shift ;;
    --skip-npu-check) SKIP_NPU_CHECK=1; shift ;;
    --skip-online-probe) SKIP_ONLINE_PROBE=1; shift ;;
    --skip-llm-reducer) SKIP_LLM_REDUCER=1; shift ;;
    --allow-newer-runtime) ALLOW_NEWER_RUNTIME=1; shift ;;
    --npu) NPU_DEVICE="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --model-path) MODEL_PATH="$2"; shift 2 ;;
    --served-model) SERVED_MODEL_NAME="$2"; shift 2 ;;
    --conda-env) CONDA_ENV="$2"; shift 2 ;;
    --run-id) RUN_ID="$2"; OUTPUT_ROOT="${SAGE_ROOT}/.sage/benchmarks/real_online_semantic_mapreduce/${RUN_ID}"; shift 2 ;;
    --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
    --events) EVENT_SIZES="$2"; shift 2 ;;
    --shards) SHARD_COUNTS="$2"; shift 2 ;;
    --top-ks) TOP_KS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

run_python() {
  if [[ -n "${CONDA_ENV}" ]]; then
    conda run -n "${CONDA_ENV}" env PYTHONPATH="${SAGE_ROOT}/src" "$@"
  else
    env PYTHONPATH="${SAGE_ROOT}/src" "$@"
  fi
}

read -r -a EVENT_ARRAY <<<"${EVENT_SIZES}"
read -r -a SHARD_ARRAY <<<"${SHARD_COUNTS}"
read -r -a TOPK_ARRAY <<<"${TOP_KS}"

if [[ "${#EVENT_ARRAY[@]}" -ne "${#SHARD_ARRAY[@]}" || "${#EVENT_ARRAY[@]}" -ne "${#TOPK_ARRAY[@]}" ]]; then
  die "--events, --shards, and --top-ks must contain the same number of entries."
fi

if [[ "${NPU_DEVICE}" != "3" && "${SAGE_ALLOW_NON_NPU3:-0}" != "1" ]]; then
  die "Refusing to use NPU ${NPU_DEVICE}. Set SAGE_ALLOW_NON_NPU3=1 only for an intentional non-NPU3 run."
fi

BASE_URL="http://127.0.0.1:${PORT}"
ENV_FILE="${DEV_HUB}/.env"
SERVER_STARTED=0
VLLM_CONTAINER_LOG_FILE="/tmp/sage-smr-vllm.redacted.log"

port_is_listening() {
  ss -ltn "sport = :${PORT}" | awk 'NR > 1 { found = 1 } END { exit(found ? 0 : 1) }'
}

require_port_free() {
  if port_is_listening; then
    die "Port ${PORT} is already listening. Use --skip-server-management only when this is the intended endpoint."
  fi
}

require_npu_free() {
  [[ "${SKIP_NPU_CHECK}" == "1" ]] && return
  command -v npu-smi >/dev/null 2>&1 || die "npu-smi not found; cannot verify NPU isolation."
  mkdir -p "${OUTPUT_ROOT}"
  npu-smi info > "${OUTPUT_ROOT}/npu-smi-before.txt" 2>/dev/null || true
  npu_process_pairs < "${OUTPUT_ROOT}/npu-smi-before.txt" | sort -u > "${OUTPUT_ROOT}/npu-smi-before-pids.txt"
  grep -q "No running processes found in NPU ${NPU_DEVICE}" "${OUTPUT_ROOT}/npu-smi-before.txt" \
    || die "NPU ${NPU_DEVICE} does not look idle. See ${OUTPUT_ROOT}/npu-smi-before.txt."
}

npu_process_pairs() {
  awk -F'|' '
    /^\|[[:space:]]*[0-9]+[[:space:]]+[0-9]+[[:space:]]*\|/ {
      split($2, device, /[[:space:]]+/)
      npu = device[2]
      pid = $3
      gsub(/[[:space:]]+/, "", pid)
      if (npu ~ /^[0-9]+$/ && pid ~ /^[0-9]+$/) {
        print npu, pid
      }
    }
  '
}

assert_managed_npu_processes_stay_on_target() {
  [[ "${SKIP_NPU_CHECK}" == "1" ]] && return
  command -v npu-smi >/dev/null 2>&1 || return

  local current_pairs="${OUTPUT_ROOT}/npu-smi-current-pids.txt"
  local container_pids="${OUTPUT_ROOT}/container-pids.txt"
  local managed_pairs="${OUTPUT_ROOT}/npu-smi-managed-pids.txt"
  npu-smi info > "${OUTPUT_ROOT}/npu-smi-current.txt" 2>/dev/null || return
  npu_process_pairs < "${OUTPUT_ROOT}/npu-smi-current.txt" | sort -u > "${current_pairs}"

  sudo -n docker top "${CONTAINER_NAME}" -eo pid 2>/dev/null \
    | awk 'NR > 1 && $1 ~ /^[0-9]+$/ { print $1 }' \
    | sort -u > "${container_pids}" || true

  awk 'NR == FNR { pids[$1] = 1; next } ($2 in pids) { print }' \
    "${container_pids}" "${current_pairs}" > "${managed_pairs}"

  if awk -v target="${NPU_DEVICE}" '$1 != target { found = 1 } END { exit(found ? 0 : 1) }' "${managed_pairs}"; then
    die "A managed container process appeared on a non-target NPU. See ${managed_pairs} and ${OUTPUT_ROOT}/npu-smi-current.txt."
  fi
}

assert_no_triton_fallback() {
  local triton_log="${OUTPUT_ROOT}/vllm-triton-check.log"

  if sudo -n docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    timeout 8s sudo -n docker exec "${CONTAINER_NAME}" sh -lc \
      "test -f '${VLLM_CONTAINER_LOG_FILE}' && tail -260 '${VLLM_CONTAINER_LOG_FILE}'" \
      > "${triton_log}" 2>/dev/null || true
  fi

  if [[ -s "${triton_log}" ]] && grep -Eq \
    "Triton not installed or not compatible|Failed to import Triton kernels|triton\\.language\\.target_info|Model Runner V2 requires Triton; using the V1 model runner" \
    "${triton_log}"; then
    die "Triton-Ascend is unavailable or vLLM fell back to the V1 model runner. See ${triton_log}."
  fi
}

wait_for_health() {
  local deadline=$((SECONDS + 900))
  while (( SECONDS < deadline )); do
    assert_managed_npu_processes_stay_on_target
    assert_no_triton_fallback
    if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
      assert_managed_npu_processes_stay_on_target
      assert_no_triton_fallback
      log "Endpoint health check passed: ${BASE_URL}/health"
      return
    fi
    sleep 5
  done
  die "Endpoint did not become healthy within 900 seconds."
}

stop_server() {
  if [[ "${SERVER_STARTED}" != "1" || "${KEEP_SERVER}" == "1" ]]; then
    return
  fi
  log "Stopping dev-hub service on port ${PORT}."
  (
    cd "${DEV_HUB}"
    VLLM_ENGINE_PORT="${PORT}" \
    VLLM_ENGINE_SYSTEMD_UNIT="${SYSTEMD_UNIT}" \
    VLLM_ENGINE_CONTAINER="${CONTAINER_NAME}" \
      bash manage.sh stop || true
  )
}

collect_diagnostics() {
  mkdir -p "${OUTPUT_ROOT}"

  {
    echo "command_line=$0 $*"
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "sage_head=$(git -C "${SAGE_ROOT}" rev-parse HEAD 2>/dev/null || true)"
    echo "container=${CONTAINER_NAME}"
    echo "systemd_unit=${SYSTEMD_UNIT}"
    echo "port=${PORT}"
    echo "npu_device=${NPU_DEVICE}"
  } > "${OUTPUT_ROOT}/run-command.env" 2>/dev/null || true

  systemctl --user --no-pager --full status "${SYSTEMD_UNIT}" \
    > "${OUTPUT_ROOT}/systemd-status.txt" 2>&1 || true
  journalctl --user -u "${SYSTEMD_UNIT}" --no-pager -n 300 \
    > "${OUTPUT_ROOT}/systemd-journal-tail.txt" 2>&1 || true

  if sudo -n docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    sudo -n docker inspect "${CONTAINER_NAME}" \
      > "${OUTPUT_ROOT}/docker-inspect.json" 2>&1 || true
    sudo -n docker top "${CONTAINER_NAME}" -eo pid,ppid,stat,etime,args \
      > "${OUTPUT_ROOT}/docker-top.txt" 2>&1 || true
    timeout 20s sudo -n docker exec "${CONTAINER_NAME}" sh -lc \
      "test -f '${VLLM_CONTAINER_LOG_FILE}' && cat '${VLLM_CONTAINER_LOG_FILE}'" \
      > "${OUTPUT_ROOT}/vllm-service.redacted.log" 2>&1 || true
  fi

  ss -ltnp > "${OUTPUT_ROOT}/ports.txt" 2>&1 || true
  npu-smi info > "${OUTPUT_ROOT}/npu-smi-exit.txt" 2>/dev/null || true
}

on_exit() {
  local exit_code=$?
  set +e
  collect_diagnostics "$@"
  stop_server
  exit "${exit_code}"
}

write_metadata() {
  mkdir -p "${OUTPUT_ROOT}"
  {
    echo "{"
    echo "  \"provenance\": \"real-online\","
    echo "  \"sage_root\": \"${SAGE_ROOT}\","
    echo "  \"run_id\": \"${RUN_ID}\","
    echo "  \"base_url\": \"${BASE_URL}\","
    echo "  \"npu_device\": \"${NPU_DEVICE}\","
    echo "  \"model_path\": \"${MODEL_PATH}\","
    echo "  \"served_model_name\": \"${SERVED_MODEL_NAME}\","
    echo "  \"conda_env\": \"${CONDA_ENV}\","
    echo "  \"git_commit\": \"$(git -C "${SAGE_ROOT}" rev-parse HEAD)\","
    echo "  \"submodules\": $(git -C "${SAGE_ROOT}" submodule status | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
    echo "}"
  } > "${OUTPUT_ROOT}/metadata.json"
}

print_plan() {
  cat <<EOF
Resolved real-online Semantic MapReduce plan
  SAGE root:      ${SAGE_ROOT}
  dev-hub:        ${DEV_HUB}
  NPU:            ${NPU_DEVICE}
  port/base URL:  ${PORT} / ${BASE_URL}
  model path:     ${MODEL_PATH}
  served model:   ${SERVED_MODEL_NAME}
  conda env:      ${CONDA_ENV}
  output root:    ${OUTPUT_ROOT}
  events:         ${EVENT_SIZES}
  shards:         ${SHARD_COUNTS}
  top-k:          ${TOP_KS}
  systemd unit:   ${SYSTEMD_UNIT}
  container:      ${CONTAINER_NAME}
  server mode:    $([[ "${SKIP_SERVER_MANAGEMENT}" == "1" ]] && echo reuse-existing || echo launch-via-dev-hub)
EOF
}

print_plan
[[ "${DRY_RUN}" == "1" ]] && exit 0
trap 'on_exit "$@"' EXIT

[[ -x "${PREPARE_RUNTIME}" ]] || die "Missing runtime preparation script: ${PREPARE_RUNTIME}"
[[ -d "${DEV_HUB}" ]] || die "Missing dev-hub submodule: ${DEV_HUB}"
[[ -d "${MODEL_PATH}" ]] || die "Model path does not exist: ${MODEL_PATH}"
[[ -f "${ENV_FILE}" ]] || die "Missing dev-hub .env with VLLM_HUST_API_KEY: ${ENV_FILE}"

mkdir -p "${OUTPUT_ROOT}"
write_metadata

if [[ "${ALLOW_NEWER_RUNTIME}" == "1" ]]; then
  "${PREPARE_RUNTIME}" --allow-newer --no-print-env | tee "${OUTPUT_ROOT}/prepare-runtime.log"
else
  "${PREPARE_RUNTIME}" --no-print-env | tee "${OUTPUT_ROOT}/prepare-runtime.log"
fi

if [[ "${SKIP_SERVER_MANAGEMENT}" == "0" ]]; then
  require_port_free
  require_npu_free
  log "Starting vLLM-HUST through dev-hub manage.sh."
  (
    cd "${DEV_HUB}"
    VLLM_ENGINE_SYSTEMD_UNIT="${SYSTEMD_UNIT}" \
    VLLM_ENGINE_CONTAINER="${CONTAINER_NAME}" \
    VLLM_ENGINE_RECREATE_CONTAINER="${SAGE_REAL_ONLINE_RECREATE_CONTAINER:-true}" \
    VLLM_ENGINE_EXTRA_ENV_KEYS=HOST_WORKSPACE_ROOT,CONTAINER_WORKSPACE_ROOT,CONTAINER_WORKDIR,VLLM_HUST_AUTO_ENABLE_CONTAINER_SSH,HUST_ASCEND_CONTAINER_NPU_DEVICES \
    HOST_WORKSPACE_ROOT="${HOST_WORKSPACE_ROOT}" \
    CONTAINER_WORKSPACE_ROOT="${CONTAINER_WORKSPACE_ROOT}" \
    CONTAINER_WORKDIR="${CONTAINER_WORKDIR}" \
    HUST_ASCEND_CONTAINER_NPU_DEVICES="${NPU_DEVICE}" \
    VLLM_ENGINE_MODEL_PATH="${MODEL_PATH}" \
    VLLM_ENGINE_SERVED_MODEL_NAME="${SERVED_MODEL_NAME}" \
    VLLM_ENGINE_PORT="${PORT}" \
    VLLM_ENGINE_TP_SIZE=1 \
    VLLM_ENGINE_NPU_DEVICES="${NPU_DEVICE}" \
    ASCEND_RT_VISIBLE_DEVICES="${NPU_DEVICE}" \
    ASCEND_VISIBLE_DEVICES="${NPU_DEVICE}" \
    VLLM_ENGINE_MAX_MODEL_LEN=2048 \
    VLLM_ENGINE_MAX_NUM_BATCHED_TOKENS=2048 \
    VLLM_ENGINE_MAX_NUM_SEQS=1 \
    VLLM_ENGINE_GPU_MEM_UTIL=0.60 \
    VLLM_ENGINE_ENABLE_CHUNKED_PREFILL=1 \
    VLLM_ENGINE_ENABLE_PREFIX_CACHING=1 \
    VLLM_ENGINE_CONTAINER_LOG_FILE="${VLLM_CONTAINER_LOG_FILE}" \
    VLLM_ENGINE_EXTRA_ARGS_JSON='["--max-num-batched-tokens","2048","--generation-config","vllm","--structured-outputs-config","{\"backend\":\"xgrammar\",\"disable_any_whitespace\":true}"]' \
    VLLM_ENGINE_PYTHON=/workspace/vllm-hust-dev-container-env/bin/python \
    VLLM_ENGINE_BIN=/workspace/vllm-hust-dev-container-env/bin/vllm \
    VLLM_ENGINE_PYTHONPATH=/workspace/SAGE/external/triton-ascend-hust/python:/workspace/SAGE/external/vllm-ascend-hust:/workspace/vllm-hust:/workspace/vllm-ascend-hust \
    COMPILE_CUSTOM_KERNELS=1 \
    VLLM_PLUGINS=ascend \
    VLLM_SEGMENT_REUSE_ENABLE=0 \
    VLLM_ASCEND_DISABLE_ADD_RMS_NORM_BIAS_CUSTOM_OP=1 \
    VLLM_ASCEND_DISABLE_TOP_K_TOP_P_CUSTOM_OP=1 \
    VLLM_ENGINE_EXTRA_ENV_PREFIXES=VLLM_KNORM_,VLLM_ASCEND_ \
      bash manage.sh start
  ) 2>&1 | tee "${OUTPUT_ROOT}/dev-hub-start.log"
  SERVER_STARTED=1
else
  log "Reusing existing endpoint on ${BASE_URL}."
fi

wait_for_health

if [[ "${SKIP_ONLINE_PROBE}" == "0" ]]; then
  log "Running smoke request."
  run_python python "${SAGE_ROOT}/tools/benchmark_carrier/run_vllm_hust_smoke_request.py" \
    --base-url "${BASE_URL}" \
    --model "${SERVED_MODEL_NAME}" \
    --env-file "${ENV_FILE}" \
    --output "${OUTPUT_ROOT}/smoke.json" \
    2>&1 | tee "${OUTPUT_ROOT}/smoke.log"

  log "Running online latency probe."
  run_python python "${SAGE_ROOT}/tools/benchmark_carrier/run_vllm_hust_online_benchmark.py" \
    --base-url "${BASE_URL}" \
    --model "${SERVED_MODEL_NAME}" \
    --env-file "${ENV_FILE}" \
    --requests 8 \
    --warmup-requests 2 \
    --concurrency 1 \
    --max-tokens 48 \
    --output-dir "${OUTPUT_ROOT}/online_probe" \
    --run-id c1 \
    2>&1 | tee "${OUTPUT_ROOT}/online-probe.log"
fi

if [[ "${SKIP_LLM_REDUCER}" == "0" ]]; then
  for index in "${!EVENT_ARRAY[@]}"; do
    events="${EVENT_ARRAY[$index]}"
    shards="${SHARD_ARRAY[$index]}"
    top_k="${TOPK_ARRAY[$index]}"
    log "Running LLM reducer workload: events=${events}, shards=${shards}, top_k=${top_k}."
    run_python python "${SAGE_ROOT}/tools/benchmark_carrier/run_large_scale_analysis_workload.py" \
      --events "${events}" \
      --shards "${shards}" \
      --seed "${SEED}" \
      --top-k "${top_k}" \
      --map-policy tail-aware \
      --reducer llm-openai \
      --llm-base-url "${BASE_URL}" \
      --llm-model "${SERVED_MODEL_NAME}" \
      --llm-env-file "${ENV_FILE}" \
      --llm-max-evidence 24 \
      --llm-max-tokens 768 \
      --llm-timeout-sec 240 \
      --llm-endpoint-type chat \
      --llm-structured-output \
      --output "${OUTPUT_ROOT}/llm-reducer-${events}e-${shards}s.json" \
      2>&1 | tee "${OUTPUT_ROOT}/llm-reducer-${events}e-${shards}s.log"
  done
fi

npu-smi info > "${OUTPUT_ROOT}/npu-smi-after.txt" 2>/dev/null || true
log "Experiment complete. Artifacts: ${OUTPUT_ROOT}"
