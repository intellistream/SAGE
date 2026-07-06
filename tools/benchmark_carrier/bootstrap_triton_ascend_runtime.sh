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

  ln -sfn "../../../third_party/ascend/backend" \
    "${root}/python/triton/backends/ascend"
  ln -sfn "../../../../third_party/ascend/language/kernels" \
    "${root}/python/triton/language/extra/kernels"
  ln -sfn "../../../../third_party/ascend/language/cann" \
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

ensure_triton_submodules() {
  local nested_ir="${TRITON_ASCEND_PATH}/third_party/ascend/AscendNPU-IR/CMakeLists.txt"
  [[ -f "${nested_ir}" ]] && return

  log "Initializing Triton-Ascend nested submodules inside the SAGE checkout."
  git -C "${TRITON_ASCEND_PATH}" submodule update --init third_party/ascend/AscendNPU-IR
  [[ -f "${nested_ir}" ]] \
    || die "Triton-Ascend nested submodule is incomplete: ${nested_ir}"
}

build_in_container() {
  sudo -n docker inspect "${DOCKER_CONTAINER}" >/dev/null 2>&1 \
    || die "Container ${DOCKER_CONTAINER} is not available for Triton-Ascend build."

  log "Building Triton-Ascend from the SAGE submodule in ${DOCKER_CONTAINER}."
  sudo -n docker exec "${DOCKER_CONTAINER}" sh -lc "
    install_build_deps() {
      if command -v dnf >/dev/null 2>&1; then
        dnf -y install zlib-devel libxml2-devel ccache
      elif command -v yum >/dev/null 2>&1; then
        yum -y install zlib-devel libxml2-devel ccache
      elif command -v apt-get >/dev/null 2>&1; then
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y zlib1g-dev libxml2-dev ccache
      else
        echo '[ERROR] No supported package manager found for Triton-Ascend build deps.' >&2
        return 1
      fi
    }

    git config --global --add safe.directory /workspace/SAGE/external/triton-ascend-hust || true
    install_build_deps
    cd /workspace/SAGE/external/triton-ascend-hust
    export TRITON_HOME=/workspace/SAGE/.sage/triton-cache
    mkdir -p \"\${TRITON_HOME}/.triton/llvm\"
    ${PYTHON_BIN} - <<'PY'
import hashlib
import os
import platform
import shutil
import subprocess
import tarfile
from pathlib import Path

base = Path('/workspace/SAGE/external/triton-ascend-hust')
cache = Path(os.environ['TRITON_HOME']) / '.triton' / 'llvm'
legacy_cache = Path(os.environ['TRITON_HOME']) / 'llvm'
rev = (base / 'cmake' / 'llvm-hash.txt').read_text()[:8]
patch_dir = base / 'third_party' / 'ascend' / 'llvm_patch'
patch_files = sorted(p for p in patch_dir.glob('*.patch') if p.is_file()) if patch_dir.is_dir() else []
h = hashlib.sha256()
for patch_file in patch_files:
    h.update(patch_file.read_bytes())
patch_hash = h.hexdigest()[:8] if patch_files else '00000000'

arch = {'x86_64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}.get(platform.machine(), platform.machine())
system_suffix = os.environ.get('TRITON_LLVM_SYSTEM_SUFFIX')
if not system_suffix:
    if platform.system() == 'Linux' and arch == 'arm64':
        system_suffix = 'ubuntu-arm64'
    else:
        raise SystemExit(f'Unsupported automatic LLVM cache platform: {platform.system()} {platform.machine()}')

name = f'llvm-{rev}-{patch_hash}-{system_suffix}'
url = f'https://triton-ascend-artifacts.obs.myhuaweicloud.com/llvm-builds/{name}.tar.gz'
package_dir = cache / name
legacy_package_dir = legacy_cache / name
version_file = package_dir / 'version.txt'
if version_file.exists() and version_file.read_text() == url:
    print(f'Using cached Triton-Ascend LLVM: {package_dir}')
else:
    tmp = cache / f'{name}.tar.gz.tmp'
    if package_dir.exists():
        shutil.rmtree(package_dir)
    legacy_version_file = legacy_package_dir / 'version.txt'
    if legacy_version_file.exists() and legacy_version_file.read_text() == url:
        print(f'Copying legacy Triton-Ascend LLVM cache into setup.py cache: {legacy_package_dir} -> {package_dir}')
        shutil.copytree(legacy_package_dir, package_dir)
    else:
        print(f'Prefetching Triton-Ascend LLVM with curl: {url}')
        subprocess.run(['curl', '-kL', '--fail', '--retry', '3', '-o', str(tmp), url], check=True)
        with tarfile.open(tmp, mode='r:gz') as tf:
            tf.extractall(cache)
        tmp.unlink(missing_ok=True)
    version_file.write_text(url)

sym = cache / f'llvm-{system_suffix}'
if sym.is_symlink() or sym.exists():
    if sym.is_symlink():
        sym.unlink()
    elif sym.is_dir():
        shutil.rmtree(sym)
    else:
        sym.unlink()
sym.symlink_to(package_dir, target_is_directory=True)
print(f'Triton-Ascend LLVM cache ready: {package_dir}')
PY
    env TRITON_BUILD_BACKENDS=ascend \
        TRITON_HOME=/workspace/SAGE/.sage/triton-cache \
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
ensure_triton_submodules
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
