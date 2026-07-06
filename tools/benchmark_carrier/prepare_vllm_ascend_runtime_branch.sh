#!/usr/bin/env bash
set -euo pipefail

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASCEND_SUBMODULE_PATH="${SAGE_ROOT}/external/vllm-ascend-hust"
DEV_HUB_SUBMODULE_PATH="${SAGE_ROOT}/external/vllm-hust-dev-hub"
RUNTIME_MANAGER_SUBMODULE_PATH="${SAGE_ROOT}/external/ascend-runtime-manager"
TRITON_ASCEND_SUBMODULE_PATH="${SAGE_ROOT}/external/triton-ascend-hust"
EXPECTED_ASCEND_BRANCH="${SAGE_VLLM_ASCEND_BRANCH:-feature/sage-semantic-mapreduce-npu-readiness}"
EXPECTED_ASCEND_COMMIT="${SAGE_VLLM_ASCEND_COMMIT:-339b27ad69aa12b8f56bbd1885c046be4e53c945}"
EXPECTED_DEV_HUB_BRANCH="${SAGE_VLLM_DEV_HUB_BRANCH:-feature/sage-semantic-mapreduce-dev-hub}"
EXPECTED_DEV_HUB_COMMIT="${SAGE_VLLM_DEV_HUB_COMMIT:-9a05905d67b31f91469b00d16d61d9146273ce87}"
EXPECTED_RUNTIME_MANAGER_BRANCH="${SAGE_ASCEND_RUNTIME_MANAGER_BRANCH:-feature/sage-semantic-mapreduce-runtime-manager}"
EXPECTED_RUNTIME_MANAGER_COMMIT="${SAGE_ASCEND_RUNTIME_MANAGER_COMMIT:-40a2afed0ae7896e004cf6d0f67c0d89e7e1582b}"
EXPECTED_TRITON_ASCEND_BRANCH="${SAGE_TRITON_ASCEND_BRANCH:-feature/sage-semantic-mapreduce-triton-runtime}"
EXPECTED_TRITON_ASCEND_COMMIT="${SAGE_TRITON_ASCEND_COMMIT:-2abb29fbeb4d3906e9fa1b7d93514ac60aa83cf0}"
CONTAINER_SAGE_ROOT="${SAGE_CONTAINER_ROOT:-/workspace/SAGE}"
CONTAINER_VLLM_HUST="${SAGE_CONTAINER_VLLM_HUST:-/workspace/vllm-hust}"
CONTAINER_VLLM_ASCEND_FALLBACK="${SAGE_CONTAINER_VLLM_ASCEND_FALLBACK:-/workspace/vllm-ascend-hust}"
STRICT_COMMIT=1
PRINT_ENV=1

usage() {
  cat <<EOF
Usage:
  tools/benchmark_carrier/prepare_vllm_ascend_runtime_branch.sh [options]

Initialize and validate the vLLM-HUST dev-hub and vLLM-Ascend-HUST submodules
used by the SAGE Semantic MapReduce NPU readiness experiments.

Options:
  --allow-newer       Allow the submodule branch to be ahead of the documented
                      pinned commit. Default: require the exact pinned commit.
  --no-print-env      Do not print dev-hub environment exports.
  -h, --help          Show this help.

Environment overrides:
  SAGE_VLLM_ASCEND_BRANCH   Default: ${EXPECTED_ASCEND_BRANCH}
  SAGE_VLLM_ASCEND_COMMIT   Default: ${EXPECTED_ASCEND_COMMIT}
  SAGE_VLLM_DEV_HUB_BRANCH  Default: ${EXPECTED_DEV_HUB_BRANCH}
  SAGE_VLLM_DEV_HUB_COMMIT  Default: ${EXPECTED_DEV_HUB_COMMIT}
  SAGE_ASCEND_RUNTIME_MANAGER_BRANCH  Default: ${EXPECTED_RUNTIME_MANAGER_BRANCH}
  SAGE_ASCEND_RUNTIME_MANAGER_COMMIT  Default: ${EXPECTED_RUNTIME_MANAGER_COMMIT}
  SAGE_TRITON_ASCEND_BRANCH Default: ${EXPECTED_TRITON_ASCEND_BRANCH}
  SAGE_TRITON_ASCEND_COMMIT Default: ${EXPECTED_TRITON_ASCEND_COMMIT}
  SAGE_CONTAINER_ROOT       Default: ${CONTAINER_SAGE_ROOT}

The dev-hub container normally mounts /home/shuhao as /workspace. The printed
VLLM_ENGINE_PYTHONPATH therefore puts the SAGE submodule first:

  /workspace/SAGE/external/triton-ascend-hust/python
  /workspace/SAGE/external/vllm-ascend-hust
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --allow-newer)
      STRICT_COMMIT=0
      shift
      ;;
    --no-print-env)
      PRINT_ENV=0
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

if [[ ! -f "${SAGE_ROOT}/.gitmodules" ]]; then
  echo "[ERROR] .gitmodules not found under ${SAGE_ROOT}" >&2
  exit 1
fi

check_submodule() {
  local label="$1"
  local path="$2"
  local branch="$3"
  local commit="$4"
  local recursive="${5:-1}"
  local relative_path="${path#"${SAGE_ROOT}/"}"
  local actual_branch
  local actual_commit

  if [[ "${recursive}" == "1" ]]; then
    git -C "${SAGE_ROOT}" submodule update --init --recursive "${relative_path}"
  else
    git -C "${SAGE_ROOT}" submodule update --init "${relative_path}"
  fi
  git -C "${path}" fetch origin "${branch}"
  git -C "${path}" checkout "${branch}"

  actual_branch="$(git -C "${path}" branch --show-current)"
  actual_commit="$(git -C "${path}" rev-parse HEAD)"

  if [[ "${actual_branch}" != "${branch}" ]]; then
    echo "[ERROR] ${label} submodule is on ${actual_branch}, expected ${branch}" >&2
    exit 1
  fi

  if [[ "${STRICT_COMMIT}" == "1" && "${actual_commit}" != "${commit}" ]]; then
    echo "[ERROR] ${label} submodule is at ${actual_commit}, expected ${commit}" >&2
    echo "[ERROR] Rerun with --allow-newer only when intentionally testing a newer project runtime commit." >&2
    exit 1
  fi

  if [[ "${STRICT_COMMIT}" != "1" ]]; then
    if ! git -C "${path}" merge-base --is-ancestor "${commit}" "${actual_commit}"; then
      echo "[ERROR] ${label} commit ${actual_commit} is not a descendant of documented commit ${commit}" >&2
      exit 1
    fi
  fi

  echo "[OK] ${label} branch is ready"
  echo "  path:   ${path}"
  echo "  branch: ${actual_branch}"
  echo "  commit: ${actual_commit}"
}

check_submodule \
  "vLLM-HUST dev-hub" \
  "${DEV_HUB_SUBMODULE_PATH}" \
  "${EXPECTED_DEV_HUB_BRANCH}" \
  "${EXPECTED_DEV_HUB_COMMIT}"

check_submodule \
  "Ascend runtime manager" \
  "${RUNTIME_MANAGER_SUBMODULE_PATH}" \
  "${EXPECTED_RUNTIME_MANAGER_BRANCH}" \
  "${EXPECTED_RUNTIME_MANAGER_COMMIT}"

check_submodule \
  "vLLM-Ascend-HUST runtime" \
  "${ASCEND_SUBMODULE_PATH}" \
  "${EXPECTED_ASCEND_BRANCH}" \
  "${EXPECTED_ASCEND_COMMIT}"

check_submodule \
  "Triton-Ascend-HUST runtime" \
  "${TRITON_ASCEND_SUBMODULE_PATH}" \
  "${EXPECTED_TRITON_ASCEND_BRANCH}" \
  "${EXPECTED_TRITON_ASCEND_COMMIT}" \
  0

if [[ "${PRINT_ENV}" == "1" ]]; then
  cat <<EOF

# dev-hub launch overrides for SAGE Semantic MapReduce NPU readiness:
export SAGE_VLLM_DEV_HUB="${SAGE_ROOT}/external/vllm-hust-dev-hub"
export VLLM_ENGINE_PYTHONPATH="${CONTAINER_SAGE_ROOT}/external/triton-ascend-hust/python:${CONTAINER_SAGE_ROOT}/external/vllm-ascend-hust:${CONTAINER_VLLM_HUST}:${CONTAINER_VLLM_ASCEND_FALLBACK}"
export COMPILE_CUSTOM_KERNELS=1
export VLLM_ASCEND_DISABLE_ADD_RMS_NORM_BIAS_CUSTOM_OP=1
export VLLM_ASCEND_DISABLE_TOP_K_TOP_P_CUSTOM_OP=1
export VLLM_ENGINE_EXTRA_ENV_PREFIXES=VLLM_KNORM_,VLLM_SEGMENT_REUSE_,VLLM_ASCEND_
EOF
fi
