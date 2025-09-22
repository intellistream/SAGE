#!/usr/bin/env bash
# Local CI runner for SAGE
# Mirrors essential steps from .github/workflows/ci.yml so you can sanity-check locally.
#
# Usage:
#   bash tools/ci/run_local_ci.sh               # default run
#   BUILD_CPP_DEPS=0 RUN_EXAMPLES=0 bash tools/ci/run_local_ci.sh
#
# Tunables (env vars):
#   PYTHON_BIN           Python executable (default: python3)
#   BUILD_CPP_DEPS       1 to install build-essential/cmake/pkg-config if needed (default: 0)
#   RUN_EXAMPLES         1 to run examples test suite (default: 1)
#   RUN_CODE_QUALITY     1 to run black/isort/flake8 checks if available (default: 1)
#   RUN_IMPORT_TESTS     1 to run basic import/CLI checks (default: 1)
#   RUN_PYPI_VALIDATE    0/1 run PyPI validation via CLI (default: 0; heavy, optional)
#
# Notes:
# - This script avoids touching your system python; it uses whatever PYTHON_BIN points to.
# - Steps that are heavy or require external services are optional and can be disabled.

set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_BIN="${PIP_BIN:-pip3}"

# By default, DO NOT attempt system package installation locally to avoid sudo prompts.
# CI runners have passwordless sudo; local machines typically don't.
BUILD_CPP_DEPS="${BUILD_CPP_DEPS:-0}"
RUN_EXAMPLES="${RUN_EXAMPLES:-1}"
RUN_CODE_QUALITY="${RUN_CODE_QUALITY:-1}"
RUN_IMPORT_TESTS="${RUN_IMPORT_TESTS:-1}"
RUN_PYPI_VALIDATE="${RUN_PYPI_VALIDATE:-0}"

echo "=== Local CI: Environment ==="
set +e
"$PYTHON_BIN" --version
"$PIP_BIN" --version
which "$PYTHON_BIN" || true
which "$PIP_BIN" || true
set -e

echo "=== Step 1: Upgrade pip ==="
"$PIP_BIN" install --upgrade pip --no-cache-dir

if [[ "$BUILD_CPP_DEPS" == "1" ]]; then
  echo "=== Step 2: Install system build deps if needed (sudo may prompt) ==="
  NEEDS_CPP=0
  if [[ -f "packages/sage-middleware/src/sage/middleware/components/sage_db/CMakeLists.txt" ]]; then
    NEEDS_CPP=1
  fi
  if [[ "$NEEDS_CPP" == "1" ]]; then
    if command -v apt-get >/dev/null 2>&1; then
  echo "Installing: build-essential cmake pkg-config"
      set +e
      SUDO_CMD=""
      if [[ $EUID -ne 0 ]]; then
        # Try passwordless sudo; if not available, skip to avoid interactive prompt
        if sudo -n true 2>/dev/null; then
          SUDO_CMD="sudo"
        else
          echo "[skip] Skipping system deps: sudo password required (non-interactive)."
          echo "      - Either preinstall deps manually (build-essential cmake pkg-config)"
          echo "      - Or rerun with BUILD_CPP_DEPS=0 (default)"
          set -e
          NEEDS_CPP=0
        fi
      fi
      if [[ "$NEEDS_CPP" == "1" ]]; then
        $SUDO_CMD apt-get update -qq && \
        $SUDO_CMD apt-get install -y --no-install-recommends \
          build-essential cmake pkg-config
        RET=$?
        set -e
        if [[ $RET -ne 0 ]]; then
          echo "[warn] System deps installation failed; continuing (C++ extensions may be unavailable)"
        fi
      fi
    else
    echo "Skipping system deps: apt-get not available on this system"
    fi
  else
    echo "C++ components not detected; skipping system deps"
  fi
else
  echo "Skipping system deps by request (BUILD_CPP_DEPS=0)"
fi

echo "=== Step 3: Install SAGE via quickstart (dev mode) ==="
chmod +x ./quickstart.sh
./quickstart.sh --dev --pip --yes

if [[ "$RUN_CODE_QUALITY" == "1" ]]; then
  echo "=== Step 4: Code Quality (best-effort) ==="
  set +e
  black --version >/dev/null 2>&1 && black --check --diff packages/ || echo "⚠️ black not installed or issues found"
  isort --version >/dev/null 2>&1 && isort --check-only --diff packages/ || echo "⚠️ isort not installed or issues found"
  flake8 --version >/dev/null 2>&1 && flake8 packages/ --count --select=E9,F63,F7,F82 --show-source --statistics || echo "⚠️ flake8 not installed or issues found"
  set -e
else
  echo "Skipping code quality checks (RUN_CODE_QUALITY=0)"
fi

if [[ "$RUN_EXAMPLES" == "1" ]]; then
  echo "=== Step 5: Run Examples Tests ==="
  chmod +x ./tools/tests/run_examples_tests.sh
  # emulate CI examples mode to reduce external deps impact
  export SAGE_EXAMPLES_MODE="test"
  set +e
  ./tools/tests/run_examples_tests.sh
  EX_RET=$?
  set -e
  if [[ $EX_RET -ne 0 ]]; then
    echo "Examples tests failed; attempting basic discovery check..."
    set +e
    "$PYTHON_BIN" tools/tests/test_examples.py analyze
    EX2_RET=$?
    set -e
    if [[ $EX2_RET -ne 0 ]]; then
      echo "❌ Basic examples discovery failed"
      exit 1
    else
      echo "✅ Basic examples discovery OK (some examples may require external services)"
    fi
  else
    echo "✅ Examples tests passed"
  fi
else
  echo "Skipping examples tests (RUN_EXAMPLES=0)"
fi

if [[ "$RUN_IMPORT_TESTS" == "1" ]]; then
  echo "=== Step 6: Basic Import & CLI Tests ==="
  set -e
  echo "Python: $("$PYTHON_BIN" --version)"
  echo "Pip: $("$PIP_BIN" --version)"
  "$PYTHON_BIN" - <<'PY'
import sys
print('Testing sage imports...')
import sage
print('✅ import sage OK, file:', getattr(sage, '__file__', 'n/a'))
import sage.common, sage.kernel, sage.libs, sage.middleware
print('✅ subpackages import OK')
PY

  if command -v sage >/dev/null 2>&1; then
    echo "✅ SAGE CLI found"
    set +e
    sage --help >/dev/null && echo "✅ CLI help OK"
    sage version && echo "✅ CLI version OK"
    set -e
  else
    echo "⚠️ SAGE CLI not in PATH; trying module entrypoint"
    set +e
    "$PYTHON_BIN" -m sage.tools.cli.main --help >/dev/null && echo "✅ CLI module works" || echo "⚠️ CLI module not available"
    set -e
  fi
else
  echo "Skipping import/CLI tests (RUN_IMPORT_TESTS=0)"
fi

if [[ "$RUN_PYPI_VALIDATE" == "1" ]]; then
  echo "=== Step 7: PyPI Release Validation (may take long) ==="
  if command -v sage >/dev/null 2>&1; then
    set +e
    timeout 1800 sage dev pypi validate --verbose || {
      RET=$?
      if [[ $RET -eq 124 ]]; then
        echo "⚠️ pypi validate timed out; trying fast mode"
        sage dev pypi validate --fast || true
      else
        echo "⚠️ pypi validate failed with code $RET; trying fast mode"
        sage dev pypi validate --fast || true
      fi
    }
    set -e
  else
    echo "⚠️ SAGE CLI not found; skip PyPI validation"
  fi
else
  echo "Skipping PyPI release validation (RUN_PYPI_VALIDATE=0)"
fi

echo "=== Local CI completed ==="
