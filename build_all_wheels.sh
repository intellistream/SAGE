#!/usr/bin/env bash
# build_all_wheels.sh
# Script to build wheel packages for all projects under packages/, packages/commercial/, and packages/tools/

set -euo pipefail

OUTPUT_DIR="wheelhouse"
mkdir -p "$OUTPUT_DIR"

# Ensure build tool is available
if ! python3 -c "import build" &>/dev/null; then
  echo "Installing build package..."
  pip install --upgrade build
fi

# Ensure setuptools-scm is available if needed for build-system.requires
if ! python3 -c "import setuptools_scm" &>/dev/null; then
  echo "Installing setuptools-scm..."
  pip install setuptools-scm
fi

# Ensure torch is available for vllm build dependencies
if ! python3 -c "import torch" &>/dev/null; then
  echo "Installing torch to satisfy build requirements..."
  pip install torch
fi

# Directories to scan
ROOTS=("packages" "packages/commercial" "packages/tools")

for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || continue
  for pkg in "$root"/*; do
    [ -d "$pkg" ] || continue
    if [ -f "$pkg/pyproject.toml" ] || [ -f "$pkg/setup.py" ]; then
      echo "Building wheel for $pkg"
      # use no isolation to leverage existing torch install and avoid strict torch==2.3.0
      (cd "$pkg" && python3 -m build --wheel --no-isolation --outdir "$OLDPWD/$OUTPUT_DIR")
    fi
  done
done

echo "All wheels built and available in $OUTPUT_DIR/"
