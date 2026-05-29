#!/usr/bin/env bash
set -euo pipefail

log() {
    printf '[%s] %s\n' "$(date -Iseconds)" "$*"
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CLUSTER_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${CLUSTER_ROOT}/../.." && pwd)"
WORKSPACE_ROOT="$(cd -- "${REPO_ROOT}/.." && pwd)"
DEPLOY_ROOT="$(cd -- "${WORKSPACE_ROOT}/.." && pwd)"

PROJECT_NAME="${SAGE_DOCKER_PROJECT_NAME:-sage-cluster8}"
RUNTIME_ENV_NAME="${SAGE_RUNTIME_ENV_NAME:-sagellm}"
RUNTIME_PYTHON="${SAGE_REMOTE_PYTHON:-/root/miniconda3/envs/${RUNTIME_ENV_NAME}/bin/python}"
BASE_CONTAINER_ID="${SAGE_BASE_CONTAINER_ID:-}"
BASE_IMAGE="${SAGE_BASE_IMAGE:-sage-cluster-runtime-base:current}"
REMOTE_REPO_ROOT="${SAGE_REMOTE_REPO_ROOT:-/workspace/SAGE}"
REMOTE_INVENTORY_PATH="${SAGE_REMOTE_INVENTORY_PATH:-/workspace/SAGE/docker/cluster8/config/flownet-cluster-8node.yaml}"
REMOTE_WORK_ROOT="${SAGE_REMOTE_WORK_ROOT:-/shared/logs/flownet}"
HOST_WORKSPACE_ROOT="${SAGE_HOST_WORKSPACE_ROOT:-${WORKSPACE_ROOT}}"
HOST_SHARED_ROOT="${SAGE_HOST_SHARED_ROOT:-${DEPLOY_ROOT}/shared}"
HEAD_CONTAINER="${SAGE_HEAD_CONTAINER:-sage-node-1}"
COMPOSE_FILE="${CLUSTER_ROOT}/compose.yaml"
LOCAL_LOCK_FILE="${CLUSTER_ROOT}/generated/${RUNTIME_ENV_NAME}-linux-64.lock.yml"
DEFAULT_RESULTS_ROOT="/shared/results/langchain_rag_shared_workloads"
LANGCHAIN_RPC_PORT="${SAGE_LANGCHAIN_RPC_PORT:-19500}"
LANGCHAIN_RPC_PARALLELISM="${SAGE_LANGCHAIN_RPC_PARALLELISM:-8}"
SAGE_GENERATION_PARALLELISM="${SAGE_GENERATION_PARALLELISM:-${LANGCHAIN_RPC_PARALLELISM}}"
SAGE_RAG_FRAMEWORKS="${SAGE_RAG_FRAMEWORKS:-sage,langchain_rpc}"
FLOWNET_ENTRY_NODE="${SAGE_FLOWNET_ENTRY_NODE:-sage-node-1:19001}"
FLOWNET_CLUSTER_NAME="${SAGE_FLOWNET_CLUSTER_NAME:-cluster8}"
REMOTE_LANGCHAIN_RPC_LOG_ROOT="${SAGE_REMOTE_LANGCHAIN_RPC_LOG_ROOT:-/shared/logs/langchain-rpc}"

export SAGE_CLUSTER_IMAGE_TAG="${SAGE_CLUSTER_IMAGE_TAG:-latest}"
export SAGE_BASE_IMAGE="${BASE_IMAGE}"
export SAGE_HOST_SHARED_ROOT="${HOST_SHARED_ROOT}"
export SAGE_HOST_WORKSPACE_ROOT="${HOST_WORKSPACE_ROOT}"
export SAGE_RUNTIME_ENV_FILE="${SAGE_RUNTIME_ENV_FILE:-generated/${RUNTIME_ENV_NAME}-linux-64.lock.yml}"
export SAGE_RUNTIME_PIP_FILE="${SAGE_RUNTIME_PIP_FILE:-generated/${RUNTIME_ENV_NAME}-linux-64.lock.pip.txt}"
export SAGE_RUNTIME_ENV_NAME

compose() {
    docker compose -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" "$@"
}

cluster_nodes() {
    printf '%s\n' \
        sage-node-1 \
        sage-node-2 \
        sage-node-3 \
        sage-node-4 \
        sage-node-5 \
        sage-node-6 \
        sage-node-7 \
        sage-node-8
}

ensure_layout() {
    mkdir -p \
        "${HOST_SHARED_ROOT}/cache/huggingface/hub" \
        "${HOST_SHARED_ROOT}/cache/huggingface/transformers" \
        "${HOST_SHARED_ROOT}/datasets" \
        "${HOST_SHARED_ROOT}/logs/container" \
        "${HOST_SHARED_ROOT}/logs/flownet" \
        "${HOST_SHARED_ROOT}/logs/langchain-rpc" \
        "${HOST_SHARED_ROOT}/results" \
        "${HOST_SHARED_ROOT}/ssh"
    chmod 700 "${HOST_SHARED_ROOT}/ssh"
    if [[ ! -f "${HOST_SHARED_ROOT}/ssh/id_ed25519" ]]; then
        log "generating dedicated cluster ssh keypair"
        ssh-keygen -q -t ed25519 -N '' -f "${HOST_SHARED_ROOT}/ssh/id_ed25519"
    fi
    chmod 600 "${HOST_SHARED_ROOT}/ssh/id_ed25519"
    chmod 644 "${HOST_SHARED_ROOT}/ssh/id_ed25519.pub"
}

require_lock_file() {
    if [[ ! -f "${LOCAL_LOCK_FILE}" ]]; then
        printf 'missing runtime lock file: %s\n' "${LOCAL_LOCK_FILE}" >&2
        exit 1
    fi
}

prepare_base_image() {
    if [[ -n "${BASE_CONTAINER_ID}" ]]; then
        log "committing base container ${BASE_CONTAINER_ID} into ${BASE_IMAGE}"
        docker commit --pause=false "${BASE_CONTAINER_ID}" "${BASE_IMAGE}" >/dev/null
        return
    fi
    if ! docker image inspect "${BASE_IMAGE}" >/dev/null 2>&1; then
        printf 'missing base image and no container id provided: %s\n' "${BASE_IMAGE}" >&2
        exit 1
    fi
}

wait_for_node_ready() {
    local node="$1"
    local timeout_s="${2:-600}"
    local deadline=$((SECONDS + timeout_s))
    while (( SECONDS <= deadline )); do
        if docker inspect --format '{{.State.Running}}' "${node}" 2>/dev/null | grep -qx true; then
            if docker exec "${node}" test -f /tmp/sage-node-ready >/dev/null 2>&1; then
                return 0
            fi
        fi
        sleep 2
    done
    printf 'node did not become ready before timeout: %s\n' "${node}" >&2
    return 1
}

wait_for_all_nodes() {
    local node
    while IFS= read -r node; do
        wait_for_node_ready "${node}"
    done < <(cluster_nodes)
}

run_in_head() {
    local command="$1"
    docker exec "${HEAD_CONTAINER}" bash -lc "${command}"
}

flow_cmd() {
    local action="$1"
    local extra_args="${2:-}"
    run_in_head \
        "cd ${REMOTE_REPO_ROOT} && ${RUNTIME_PYTHON} -m sage.runtime.flownet.cli ${action} --inventory ${REMOTE_INVENTORY_PATH} ${extra_args}"
}

cluster_up() {
    wait_for_all_nodes
    flow_cmd \
        'cluster up' \
        "--remote-repo-root ${REMOTE_REPO_ROOT} --remote-inventory-path ${REMOTE_INVENTORY_PATH} --remote-python ${RUNTIME_PYTHON} --remote-work-root ${REMOTE_WORK_ROOT} --ssh-user root --ssh-identity-file /root/.ssh/id_ed25519"
}

cluster_down() {
    wait_for_node_ready "${HEAD_CONTAINER}" 120
    flow_cmd \
        'cluster down' \
        "--remote-work-root ${REMOTE_WORK_ROOT} --ssh-user root --ssh-identity-file /root/.ssh/id_ed25519"
}

run_rag() {
    shift || true
    local extra_args=("$@")
    local quoted_args=""
    local arg
    for arg in "${extra_args[@]}"; do
        printf -v quoted_args '%s %q' "${quoted_args}" "${arg}"
    done
    run_in_head \
        "cd ${REMOTE_REPO_ROOT} && mkdir -p ${DEFAULT_RESULTS_ROOT} && export HF_HOME=/shared/cache/huggingface && export HUGGINGFACE_HUB_CACHE=/shared/cache/huggingface/hub && export TRANSFORMERS_CACHE=/shared/cache/huggingface/transformers && ${RUNTIME_PYTHON} evaluation/run_langchain_sage_rag_experiment.py --output-root ${DEFAULT_RESULTS_ROOT}${quoted_args}"
}

langchain_rpc_endpoints_csv() {
    local endpoint_csv=""
    local node
    while IFS= read -r node; do
        if [[ -n "${endpoint_csv}" ]]; then
            endpoint_csv+=","
        fi
        endpoint_csv+="${node}:${LANGCHAIN_RPC_PORT}"
    done < <(cluster_nodes)
    printf '%s\n' "${endpoint_csv}"
}

wait_for_langchain_rpc_worker() {
    local node="$1"
    local timeout_s="${2:-120}"
    local deadline=$((SECONDS + timeout_s))
    while (( SECONDS <= deadline )); do
        if run_in_head "${RUNTIME_PYTHON} -c \"import sys, xmlrpc.client; proxy = xmlrpc.client.ServerProxy('http://${node}:${LANGCHAIN_RPC_PORT}/RPC2', allow_none=True); result = proxy.ping(); sys.exit(0 if result.get('status') == 'ok' else 1)\"" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    printf 'langchain rpc worker did not become ready before timeout: %s\n' "${node}" >&2
    return 1
}

langchain_rpc_up() {
    ensure_layout
    wait_for_all_nodes
    local node
    while IFS= read -r node; do
        docker exec "${node}" bash -lc "mkdir -p ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}"
        docker exec "${node}" bash -lc "worker_pattern='^${RUNTIME_PYTHON} -m evaluation.langchain_rag.rpc_worker --host 0.0.0.0 --port ${LANGCHAIN_RPC_PORT} --node-id ${node}\$'; if [[ -f ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}/${node}.pid ]]; then kill \$(cat ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}/${node}.pid) >/dev/null 2>&1 || true; rm -f ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}/${node}.pid; fi; pkill -f \"\${worker_pattern}\" >/dev/null 2>&1 || true; cd ${REMOTE_REPO_ROOT} && nohup ${RUNTIME_PYTHON} -m evaluation.langchain_rag.rpc_worker --host 0.0.0.0 --port ${LANGCHAIN_RPC_PORT} --node-id ${node} > ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}/${node}.log 2>&1 < /dev/null & printf '%s\n' \$! > ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}/${node}.pid"
        wait_for_langchain_rpc_worker "${node}"
    done < <(cluster_nodes)
}

langchain_rpc_down() {
    local node
    while IFS= read -r node; do
        docker exec "${node}" bash -lc "worker_pattern='^${RUNTIME_PYTHON} -m evaluation.langchain_rag.rpc_worker --host 0.0.0.0 --port ${LANGCHAIN_RPC_PORT} --node-id ${node}\$'; if [[ -f ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}/${node}.pid ]]; then kill \$(cat ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}/${node}.pid) >/dev/null 2>&1 || true; rm -f ${REMOTE_LANGCHAIN_RPC_LOG_ROOT}/${node}.pid; fi; pkill -f \"\${worker_pattern}\" >/dev/null 2>&1 || true" >/dev/null 2>&1 || true
    done < <(cluster_nodes)
}

run_rag_distributed() {
    shift || true
    local endpoints
    endpoints="$(langchain_rpc_endpoints_csv)"
    langchain_rpc_up
    run_rag run-rag \
    --frameworks "${SAGE_RAG_FRAMEWORKS}" \
        --sage-runtime-platform flownet \
        --flownet-session-mode connect \
        --flownet-entry-node "${FLOWNET_ENTRY_NODE}" \
        --flownet-cluster "${FLOWNET_CLUSTER_NAME}" \
    --generation-parallelism "${SAGE_GENERATION_PARALLELISM}" \
        --langchain-rpc-endpoints "${endpoints}" \
        --langchain-rpc-parallelism "${LANGCHAIN_RPC_PARALLELISM}" \
        "$@"
}

usage() {
    cat <<'EOF'
Usage: host_cluster_ctl.sh <command> [args...]

Commands:
  prepare      Create shared directories and the cluster SSH keypair.
  build        Build the Docker image used by all 8 nodes.
  compose-up   Start the 8-node Docker compose stack.
  compose-down Stop and remove the Docker compose stack.
  plan         Print the resolved 8-node FlowNet inventory plan.
  cluster-up   Start FlowNet on all running nodes through in-cluster SSH.
  cluster-down Stop FlowNet on all running nodes.
    langchain-rpc-up   Start LangChain RPC workers on all 8 nodes.
    langchain-rpc-down Stop LangChain RPC workers on all 8 nodes.
  status       Print FlowNet cluster status from the head node.
  all-up       Run compose-up, cluster-up, then status.
  all-down     Run cluster-down, then compose-down.
  run-rag      Run the LangChain + SAGE RAG experiment inside the head node.
    run-rag-distributed  Run the 8-node FlowNet SAGE vs LangChain RPC comparison.
EOF
}

main() {
    local command="${1:-}"
    case "${command}" in
        prepare)
            ensure_layout
            ;;
        build)
            ensure_layout
            require_lock_file
            prepare_base_image
            compose build
            ;;
        compose-up)
            ensure_layout
            require_lock_file
            prepare_base_image
            compose up -d --build
            ;;
        compose-down)
            compose down --remove-orphans
            ;;
        plan)
            wait_for_node_ready "${HEAD_CONTAINER}" 120
            flow_cmd 'cluster plan' '--format text'
            ;;
        cluster-up)
            cluster_up
            ;;
        cluster-down)
            cluster_down
            ;;
        langchain-rpc-up)
            langchain_rpc_up
            ;;
        langchain-rpc-down)
            langchain_rpc_down
            ;;
        status)
            wait_for_node_ready "${HEAD_CONTAINER}" 120
            flow_cmd 'cluster status' '--timeout 5.0'
            ;;
        all-up)
            ensure_layout
            require_lock_file
            prepare_base_image
            compose up -d --build
            cluster_up
            wait_for_node_ready "${HEAD_CONTAINER}" 120
            flow_cmd 'cluster status' '--timeout 5.0'
            ;;
        all-down)
            langchain_rpc_down || true
            cluster_down || true
            compose down --remove-orphans
            ;;
        run-rag)
            wait_for_node_ready "${HEAD_CONTAINER}" 120
            run_rag "$@"
            ;;
        run-rag-distributed)
            wait_for_node_ready "${HEAD_CONTAINER}" 120
            run_rag_distributed "$@"
            ;;
        ""|help|-h|--help)
            usage
            ;;
        *)
            printf 'unsupported command: %s\n' "${command}" >&2
            usage >&2
            exit 1
            ;;
    esac
}

main "$@"
