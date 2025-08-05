#!/usr/bin/env bash
# build_all_wheels.sh
# Script to build wheel packages for all projects under packages/, packages/commercial/, and packages/tools/

set -euo pipefail

<<<<<<< HEAD
<<<<<<< HEAD
OUTPUT_DIR="build/wheels"
=======
OUTPUT_DIR="wheelhouse"
>>>>>>> 7e283a1 (code cleanups)
=======
OUTPUT_DIR="build/wheels"
>>>>>>> e3ad356 (renames)
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

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> e3ad356 (renames)
# Install Rust if not available (required for tokenizers and other Rust-based packages)
if ! command -v rustc &> /dev/null; then
    echo "Installing Rust toolchain for tokenizers compilation..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    source ~/.cargo/env
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "Rust installed successfully"
else
    echo "Rust is already available"
<<<<<<< HEAD
fi

# Pre-install dependencies to avoid compilation issues during wheel building
echo "Pre-installing common dependencies..."
pip install --upgrade httpx[socks] socksio

=======
# Ensure torch is available for vllm build dependencies
if ! python3 -c "import torch" &>/dev/null; then
  echo "Installing torch to satisfy build requirements..."
  pip install torch
fi

>>>>>>> 7e283a1 (code cleanups)
=======
fi

# Pre-install dependencies to avoid compilation issues during wheel building
echo "Pre-installing common dependencies..."
pip install --upgrade httpx[socks] socksio

>>>>>>> e3ad356 (renames)
# Directories to scan
ROOTS=("packages" "packages/commercial" "packages/tools")

for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || continue
  for pkg in "$root"/*; do
    [ -d "$pkg" ] || continue
    if [ -f "$pkg/pyproject.toml" ] || [ -f "$pkg/setup.py" ]; then
      echo "Building wheel for $pkg"
      # use no isolation to leverage existing torch install and avoid strict torch==2.3.0
<<<<<<< HEAD
      # add --no-build-isolation and set PIP_NO_BUILD_ISOLATION to speed up dependency resolution
      export PIP_NO_BUILD_ISOLATION=1
      export PIP_DISABLE_PIP_VERSION_CHECK=1
=======
>>>>>>> 7e283a1 (code cleanups)
      (cd "$pkg" && python3 -m build --wheel --no-isolation --outdir "$OLDPWD/$OUTPUT_DIR")
    fi
  done
done

echo "All wheels built and available in $OUTPUT_DIR/"
