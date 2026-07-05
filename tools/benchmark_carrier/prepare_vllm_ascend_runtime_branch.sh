#!/usr/bin/env bash
set -euo pipefail

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SUBMODULE_PATH="${SAGE_ROOT}/external/vllm-ascend-hust"
EXPECTED_BRANCH="${SAGE_VLLM_ASCEND_BRANCH:-feature/sage-semantic-mapreduce-npu-readiness}"
EXPECTED_COMMIT="${SAGE_VLLM_ASCEND_COMMIT:-b8a09892162872ef7ba509434f6000b24480fd5c}"
CONTAINER_SAGE_ROOT="${SAGE_CONTAINER_ROOT:-/workspace/SAGE}"
CONTAINER_VLLM_HUST="${SAGE_CONTAINER_VLLM_HUST:-/workspace/vllm-hust}"
CONTAINER_VLLM_ASCEND_FALLBACK="${SAGE_CONTAINER_VLLM_ASCEND_FALLBACK:-/workspace/vllm-ascend-hust}"
STRICT_COMMIT=1
PRINT_ENV=1

usage() {
  cat <<EOF
Usage:
  tools/benchmark_carrier/prepare_vllm_ascend_runtime_branch.sh [options]

Initialize and validate the vLLM-Ascend-HUST submodule used by the SAGE
Semantic MapReduce NPU readiness experiments.

Options:
  --allow-newer       Allow the submodule branch to be ahead of the documented
                      pinned commit. Default: require the exact pinned commit.
  --no-print-env      Do not print dev-hub environment exports.
  -h, --help          Show this help.

Environment overrides:
  SAGE_VLLM_ASCEND_BRANCH   Default: ${EXPECTED_BRANCH}
  SAGE_VLLM_ASCEND_COMMIT   Default: ${EXPECTED_COMMIT}
  SAGE_CONTAINER_ROOT       Default: ${CONTAINER_SAGE_ROOT}

The dev-hub container normally mounts /home/shuhao as /workspace. The printed
VLLM_ENGINE_PYTHONPATH therefore puts the SAGE submodule first:

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

git -C "${SAGE_ROOT}" submodule update --init --recursive external/vllm-ascend-hust
git -C "${SUBMODULE_PATH}" fetch origin "${EXPECTED_BRANCH}"
git -C "${SUBMODULE_PATH}" checkout "${EXPECTED_BRANCH}"

actual_branch="$(git -C "${SUBMODULE_PATH}" branch --show-current)"
actual_commit="$(git -C "${SUBMODULE_PATH}" rev-parse HEAD)"

if [[ "${actual_branch}" != "${EXPECTED_BRANCH}" ]]; then
  echo "[ERROR] vLLM-Ascend-HUST submodule is on ${actual_branch}, expected ${EXPECTED_BRANCH}" >&2
  exit 1
fi

if [[ "${STRICT_COMMIT}" == "1" && "${actual_commit}" != "${EXPECTED_COMMIT}" ]]; then
  echo "[ERROR] vLLM-Ascend-HUST submodule is at ${actual_commit}, expected ${EXPECTED_COMMIT}" >&2
  echo "[ERROR] Rerun with --allow-newer only when intentionally testing a newer project runtime commit." >&2
  exit 1
fi

if [[ "${STRICT_COMMIT}" != "1" ]]; then
  if ! git -C "${SUBMODULE_PATH}" merge-base --is-ancestor "${EXPECTED_COMMIT}" "${actual_commit}"; then
    echo "[ERROR] ${actual_commit} is not a descendant of documented commit ${EXPECTED_COMMIT}" >&2
    exit 1
  fi
fi

echo "[OK] vLLM-Ascend-HUST runtime branch is ready"
echo "  path:   ${SUBMODULE_PATH}"
echo "  branch: ${actual_branch}"
echo "  commit: ${actual_commit}"

if [[ "${PRINT_ENV}" == "1" ]]; then
  cat <<EOF

# dev-hub launch overrides for SAGE Semantic MapReduce NPU readiness:
export VLLM_ENGINE_PYTHONPATH="${CONTAINER_SAGE_ROOT}/external/vllm-ascend-hust:${CONTAINER_VLLM_HUST}:${CONTAINER_VLLM_ASCEND_FALLBACK}"
export COMPILE_CUSTOM_KERNELS=1
export VLLM_ASCEND_DISABLE_ADD_RMS_NORM_BIAS_CUSTOM_OP=1
export VLLM_ASCEND_DISABLE_TOP_K_TOP_P_CUSTOM_OP=1
export VLLM_ENGINE_EXTRA_ENV_PREFIXES=VLLM_KNORM_,VLLM_SEGMENT_REUSE_,VLLM_ASCEND_
EOF
fi
