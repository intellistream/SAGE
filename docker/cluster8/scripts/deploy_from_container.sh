#!/usr/bin/env bash
set -euo pipefail

log() {
    printf '[%s] %s\n' "$(date -Iseconds)" "$*"
}

require_cmd() {
    local tool="$1"
    if ! command -v "${tool}" >/dev/null 2>&1; then
        printf 'missing required command: %s\n' "${tool}" >&2
        exit 1
    fi
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CLUSTER_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${CLUSTER_ROOT}/../.." && pwd)"
WORKSPACE_ROOT="$(cd -- "${REPO_ROOT}/.." && pwd)"
EXTERNAL_WORKSPACE_ROOT="${SAGE_EXTERNAL_WORKSPACE_ROOT:-/root/workspace}"
EDITABLE_REPO_MANIFEST="${CLUSTER_ROOT}/config/editable-repos.txt"

DOCKER_HOST_SSH="${SAGE_DOCKER_HOST:-user@11.11.11.32}"
HOST_DEPLOY_ROOT="${SAGE_HOST_DEPLOY_ROOT:-/home/user/sage-docker-cluster}"
HOST_WORKSPACE_ROOT="${HOST_DEPLOY_ROOT}/workspace"
RUNTIME_ENV_NAME="${SAGE_RUNTIME_ENV_NAME:-${CONDA_DEFAULT_ENV:-sagellm}}"
LOCK_FILE="${CLUSTER_ROOT}/generated/${RUNTIME_ENV_NAME}-linux-64.lock.yml"
LOCAL_PYTHON="${SAGE_LOCAL_PYTHON:-$(command -v python)}"
CURRENT_CONTAINER_ID="${SAGE_BASE_CONTAINER_ID:-$(hostname)}"
BASE_IMAGE_NAME="${SAGE_BASE_IMAGE:-sage-cluster-runtime-base:current}"
HOST_DEPLOY_LOG="${HOST_DEPLOY_ROOT}/shared/logs/cluster8-all-up.log"
HOST_DEPLOY_STATUS="${HOST_DEPLOY_ROOT}/shared/logs/cluster8-all-up.exit"
HOST_DEPLOY_TIMEOUT_SECONDS="${SAGE_HOST_DEPLOY_TIMEOUT_SECONDS:-7200}"

require_cmd ssh
require_cmd rsync
require_cmd "${LOCAL_PYTHON}"

log "checking host prerequisites on ${DOCKER_HOST_SSH}"
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "${DOCKER_HOST_SSH}" \
    'command -v docker >/dev/null && docker compose version >/dev/null && command -v rsync >/dev/null'

log "exporting runtime environment lock for ${RUNTIME_ENV_NAME}"
"${LOCAL_PYTHON}" "${CLUSTER_ROOT}/scripts/export_runtime_env_lock.py" \
    --env-name "${RUNTIME_ENV_NAME}" \
    --output "${LOCK_FILE}"

log "preparing host directories"
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "${DOCKER_HOST_SSH}" \
    "mkdir -p '${HOST_WORKSPACE_ROOT}' '${HOST_DEPLOY_ROOT}/shared' '${HOST_DEPLOY_ROOT}/shared/logs'"

log "stopping any in-flight host cluster build"
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "${DOCKER_HOST_SSH}" \
    "pkill -f '^docker compose -f ${HOST_WORKSPACE_ROOT}/SAGE/docker/cluster8/compose.yaml -p sage-cluster8 up -d --build$' >/dev/null 2>&1 || true; pkill -f '^/root/miniconda3/envs/${RUNTIME_ENV_NAME}/bin/python -m pip install --no-deps -r /tmp/runtime-pip.lock.txt$' >/dev/null 2>&1 || true"

log "syncing workspace to ${DOCKER_HOST_SSH}:${HOST_WORKSPACE_ROOT}"
rsync -az --delete \
    -e 'ssh -o BatchMode=yes -o StrictHostKeyChecking=no' \
    --exclude='.git/' \
    --exclude='**/__pycache__/' \
    --exclude='**/.mypy_cache/' \
    --exclude='**/.pytest_cache/' \
    --exclude='**/.ruff_cache/' \
    --exclude='**/*.pyc' \
    --exclude='**/node_modules/' \
    --exclude='SAGE/evaluation/results/' \
    "${WORKSPACE_ROOT}/" "${DOCKER_HOST_SSH}:${HOST_WORKSPACE_ROOT}/"

if [[ -f "${EDITABLE_REPO_MANIFEST}" ]]; then
    while IFS= read -r repo_name; do
        repo_name="${repo_name//[$'\r\n']/}"
        if [[ -z "${repo_name}" ]]; then
            continue
        fi
        if [[ ! -d "${EXTERNAL_WORKSPACE_ROOT}/${repo_name}" ]]; then
            continue
        fi
        log "syncing editable dependency repo ${repo_name}"
        rsync -az --delete \
            -e 'ssh -o BatchMode=yes -o StrictHostKeyChecking=no' \
            --exclude='.git/' \
            --exclude='**/__pycache__/' \
            --exclude='**/.mypy_cache/' \
            --exclude='**/.pytest_cache/' \
            --exclude='**/.ruff_cache/' \
            --exclude='**/*.pyc' \
            "${EXTERNAL_WORKSPACE_ROOT}/${repo_name}/" \
            "${DOCKER_HOST_SSH}:${HOST_WORKSPACE_ROOT}/${repo_name}/"
    done <"${EDITABLE_REPO_MANIFEST}"
fi

log "starting compose stack and FlowNet cluster on host"
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "${DOCKER_HOST_SSH}" \
    "rm -f '${HOST_DEPLOY_STATUS}'; nohup bash -lc 'env SAGE_RUNTIME_ENV_NAME=\"${RUNTIME_ENV_NAME}\" SAGE_BASE_CONTAINER_ID=\"${CURRENT_CONTAINER_ID}\" SAGE_BASE_IMAGE=\"${BASE_IMAGE_NAME}\" bash \"${HOST_WORKSPACE_ROOT}/SAGE/docker/cluster8/scripts/host_cluster_ctl.sh\" all-up; printf \"%s\\n\" \$? > \"${HOST_DEPLOY_STATUS}\"' >'${HOST_DEPLOY_LOG}' 2>&1 < /dev/null &"

log "waiting for host deployment job to finish"
start_time="$(date +%s)"
while true; do
    if ssh -o BatchMode=yes -o StrictHostKeyChecking=no "${DOCKER_HOST_SSH}" "test -f '${HOST_DEPLOY_STATUS}'"; then
        break
    fi

    current_time="$(date +%s)"
    if (( current_time - start_time > HOST_DEPLOY_TIMEOUT_SECONDS )); then
        printf 'timed out waiting for host deployment after %s seconds\n' "${HOST_DEPLOY_TIMEOUT_SECONDS}" >&2
        exit 1
    fi

    log "host deployment still running; recent host log tail follows"
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no "${DOCKER_HOST_SSH}" \
        "tail -n 20 '${HOST_DEPLOY_LOG}' 2>/dev/null || true"
    sleep 15
done

host_exit_code="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no "${DOCKER_HOST_SSH}" "cat '${HOST_DEPLOY_STATUS}'")"
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "${DOCKER_HOST_SSH}" \
    "tail -n 200 '${HOST_DEPLOY_LOG}' 2>/dev/null || true"

if [[ "${host_exit_code}" != "0" ]]; then
    printf 'host deployment failed with exit code %s\n' "${host_exit_code}" >&2
    exit "${host_exit_code}"
fi

log "cluster deployment completed"
