#!/usr/bin/env bash
# build_all_wheels.sh
# Script to build wheel packages for all projects under packages/, packages/commercial/, and packages/tools/

set -euo pipefail

OUTPUT_DIR="build/wheels"
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

# Install Rust if not available (required for tokenizers and other Rust-based packages)
if ! command -v rustc &> /dev/null; then
    echo "Installing Rust toolchain for tokenizers compilation..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    source ~/.cargo/env
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "Rust installed successfully"
else
    echo "Rust is already available"
fi

# Pre-install dependencies to avoid compilation issues during wheel building
echo "Pre-installing common dependencies..."
pip install --upgrade httpx[socks] socksio

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
