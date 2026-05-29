#!/usr/bin/env bash
set -euo pipefail

log() {
    printf '[%s] %s\n' "$(date -Iseconds)" "$*"
}

runtime_env="${SAGE_RUNTIME_ENV_NAME:-sagellm}"
runtime_python="/root/miniconda3/envs/${runtime_env}/bin/python"
repo_root="${SAGE_REPO_ROOT:-/workspace/SAGE}"
workloads_root="${SAGE_WORKLOADS_ROOT:-/workspace/llm-serving-workloads}"
shared_data_root="${SAGE_SHARED_DATA_ROOT:-/shared/datasets}"
shared_results_root="${SAGE_SHARED_RESULTS_ROOT:-/shared/results}"
shared_log_root="${SAGE_SHARED_LOG_ROOT:-/shared/logs}"
shared_cache_root="${SAGE_SHARED_CACHE_ROOT:-/shared/cache}"
cluster_ssh_dir="${SAGE_CLUSTER_SSH_DIR:-/opt/sage-cluster/ssh}"
editable_repo_manifest="${repo_root}/docker/cluster8/config/editable-repos.txt"
node_id="${SAGE_NODE_ID:-unknown-node}"
bootstrap_stamp="/tmp/sage-editable-installed"
bootstrap_log="${shared_log_root}/container/${node_id}.bootstrap.log"

mkdir -p \
    /root/.ssh \
    /var/run/sshd \
    "${shared_cache_root}/huggingface/hub" \
    "${shared_cache_root}/huggingface/transformers" \
    "${shared_cache_root}/sage" \
    "${shared_data_root}" \
    "${shared_log_root}/container" \
    "${shared_log_root}/flownet" \
    "${shared_results_root}"
chmod 700 /root/.ssh

exec > >(tee -a "${bootstrap_log}") 2>&1

if [[ ! -x "${runtime_python}" ]]; then
    log "missing runtime python: ${runtime_python}"
    exit 1
fi
if [[ ! -d "${repo_root}" ]]; then
    log "missing repo root: ${repo_root}"
    exit 1
fi
if [[ ! -f "${cluster_ssh_dir}/id_ed25519" || ! -f "${cluster_ssh_dir}/id_ed25519.pub" ]]; then
    log "missing cluster ssh keypair under ${cluster_ssh_dir}"
    exit 1
fi

install -m 0600 "${cluster_ssh_dir}/id_ed25519" /root/.ssh/id_ed25519
install -m 0644 "${cluster_ssh_dir}/id_ed25519.pub" /root/.ssh/id_ed25519.pub
install -m 0644 "${cluster_ssh_dir}/id_ed25519.pub" /root/.ssh/authorized_keys
cat >/root/.ssh/config <<'EOF'
Host *
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  LogLevel ERROR
EOF
chmod 600 /root/.ssh/authorized_keys /root/.ssh/config

export HF_HOME="${HF_HOME:-${shared_cache_root}/huggingface}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${shared_cache_root}/huggingface/hub}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${shared_cache_root}/huggingface/transformers}"

if [[ ! -f "${bootstrap_stamp}" ]]; then
    log "installing editable workspace packages into ${runtime_env}"
    if [[ -f "${editable_repo_manifest}" ]]; then
        while IFS= read -r repo_name; do
            repo_name="${repo_name//[$'\r\n']/}"
            if [[ -z "${repo_name}" ]]; then
                continue
            fi
            if [[ ! -d "/workspace/${repo_name}" ]]; then
                continue
            fi
            "${runtime_python}" -m pip install --disable-pip-version-check --no-deps -e "/workspace/${repo_name}"
        done <"${editable_repo_manifest}"
    fi
    "${runtime_python}" -m pip install --disable-pip-version-check --no-deps -e "${repo_root}"
    if [[ -d "${workloads_root}" ]]; then
        "${runtime_python}" -m pip install --disable-pip-version-check --no-deps -e "${workloads_root}"
    fi
    touch "${bootstrap_stamp}"
fi

touch /tmp/sage-node-ready
log "container bootstrap complete for ${node_id}; starting sshd"
exec /usr/sbin/sshd -D -e
