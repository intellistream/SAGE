#!/usr/bin/env bash
set -euo pipefail

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TRITON_ASCEND_PATH="${SAGE_TRITON_ASCEND_PATH:-${SAGE_ROOT}/external/triton-ascend-hust}"
TRITON_ASCEND_CACHE="${SAGE_TRITON_ASCEND_BUILD_CACHE:-}"
PYTHON_BIN="${SAGE_TRITON_ASCEND_PYTHON:-/workspace/vllm-hust-dev-container-env/bin/python}"
DOCKER_CONTAINER="${SAGE_TRITON_ASCEND_CONTAINER:-sage-smr-npu3}"
AUTO_BUILD="${SAGE_TRITON_ASCEND_AUTO_BUILD:-0}"

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_path() {
  [[ -e "$1" ]] || die "$2: $1"
}

link_backend_tree() {
  local root="$1"

  mkdir -p "${root}/python/triton/backends"
  mkdir -p "${root}/python/triton/language/extra"
  mkdir -p "${root}/python/triton/tools/extra"

  ln -sfn "${root}/third_party/ascend/backend" \
    "${root}/python/triton/backends/ascend"
  ln -sfn "${root}/third_party/ascend/language/kernels" \
    "${root}/python/triton/language/extra/kernels"
  ln -sfn "${root}/third_party/ascend/language/cann" \
    "${root}/python/triton/language/extra/cann"
}

runtime_is_ready() {
  [[ -f "${TRITON_ASCEND_PATH}/python/triton/_C/libtriton.so" ]] \
    && [[ -f "${TRITON_ASCEND_PATH}/python/triton/_C/libentryC.so" ]] \
    && [[ -f "${TRITON_ASCEND_PATH}/python/triton/_C/triton-mlir-opt" ]] \
    && [[ -f "${TRITON_ASCEND_PATH}/python/triton/language/target_info.py" ]] \
    && [[ -f "${TRITON_ASCEND_PATH}/python/triton_kernels/triton_kernels/matmul_ogs.py" ]] \
    && [[ -e "${TRITON_ASCEND_PATH}/python/triton/backends/ascend" ]]
}

copy_from_cache() {
  [[ -n "${TRITON_ASCEND_CACHE}" ]] || return 1
  [[ -d "${TRITON_ASCEND_CACHE}" ]] || return 1
  [[ "$(git -C "${TRITON_ASCEND_CACHE}" rev-parse HEAD 2>/dev/null)" == \
     "$(git -C "${TRITON_ASCEND_PATH}" rev-parse HEAD 2>/dev/null)" ]] || return 1
  [[ -d "${TRITON_ASCEND_CACHE}/python/triton/_C" ]] || return 1

  log "Using same-commit Triton-Ascend build cache: ${TRITON_ASCEND_CACHE}"
  rm -rf "${TRITON_ASCEND_PATH}/python/triton/_C"
  cp -a "${TRITON_ASCEND_CACHE}/python/triton/_C" \
    "${TRITON_ASCEND_PATH}/python/triton/_C"
  link_backend_tree "${TRITON_ASCEND_PATH}"
}

build_in_container() {
  sudo -n docker inspect "${DOCKER_CONTAINER}" >/dev/null 2>&1 \
    || die "Container ${DOCKER_CONTAINER} is not available for Triton-Ascend build."

  log "Building Triton-Ascend from the SAGE submodule in ${DOCKER_CONTAINER}."
  sudo -n docker exec "${DOCKER_CONTAINER}" sh -lc "
    git config --global --add safe.directory /workspace/SAGE/external/triton-ascend-hust || true
    cd /workspace/SAGE/external/triton-ascend-hust
    env TRITON_BUILD_BACKENDS=ascend \
        TRITON_BUILD_WITH_CLANG_LLD=false \
        TRITON_BUILD_WITH_CCACHE=true \
        TRITON_BUILD_PROTON=OFF \
        TRITON_APPEND_CMAKE_ARGS='-DTRITON_BUILD_UT=OFF' \
        MAX_JOBS=\${MAX_JOBS:-8} \
        ${PYTHON_BIN} -m pip install -e . --no-build-isolation -v
  "
}

verify_imports() {
  sudo -n docker inspect "${DOCKER_CONTAINER}" >/dev/null 2>&1 || return 0

  sudo -n docker exec "${DOCKER_CONTAINER}" sh -lc "
    timeout 45s env PYTHONPATH=/workspace/SAGE/external/triton-ascend-hust/python/triton_kernels:/workspace/SAGE/external/triton-ascend-hust/python:/workspace/SAGE/external/vllm-hust:/workspace/SAGE/external/vllm-ascend-hust \
      ${PYTHON_BIN} - <<'PY'
import importlib
for module in [
    'triton',
    'triton.backends',
    'triton.language.target_info',
    'triton_kernels',
    'triton_kernels.matmul_ogs',
]:
    importlib.import_module(module)
print('Triton-Ascend runtime import probe passed.')
PY
  "
}

require_path "${TRITON_ASCEND_PATH}" "Triton-Ascend submodule not found"
link_backend_tree "${TRITON_ASCEND_PATH}"

if ! runtime_is_ready; then
  if ! copy_from_cache; then
    [[ "${AUTO_BUILD}" == "1" ]] \
      || die "Triton-Ascend runtime is not built under ${TRITON_ASCEND_PATH}. Set SAGE_TRITON_ASCEND_BUILD_CACHE to a same-commit built checkout, or set SAGE_TRITON_ASCEND_AUTO_BUILD=1 after configuring the container CA/LLVM cache."
    build_in_container
  fi
fi

runtime_is_ready || die "Triton-Ascend runtime bootstrap did not produce a complete runtime."
verify_imports
log "Triton-Ascend runtime is ready: ${TRITON_ASCEND_PATH}"
