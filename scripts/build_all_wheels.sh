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

# Verify build installation
if ! python3 -c "from build import ProjectBuilder; print('build module working')" &>/dev/null; then
  echo "Re-installing build with proper dependencies..."
  pip uninstall -y build
  pip install --upgrade build[virtualenv]
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

echo "Collecting all project dependencies for download..."
# gather main dependencies from pyproject.toml of each package
TMP_REQS=$(mktemp)
for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || continue
  for TOML in "$root"/*/pyproject.toml; do
    [ -f "$TOML" ] || continue
    python3 -c "
import tomllib
with open('$TOML', 'rb') as f:
    data = tomllib.load(f)
for dep in data.get('project', {}).get('dependencies', []):
    # strip version specifiers
    print(dep.split()[0])
" >> "$TMP_REQS"
  done
done

if [ -s "$TMP_REQS" ]; then
  echo "Downloading dependencies to wheelhouse..."
  pip download --dest "$OUTPUT_DIR" --no-deps -r "$TMP_REQS" || echo "Warning: Some dependencies could not be downloaded"
fi
rm "$TMP_REQS"

for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || continue
  for pkg in "$root"/*; do
    [ -d "$pkg" ] || continue
    if [ -f "$pkg/pyproject.toml" ] || [ -f "$pkg/setup.py" ]; then
      echo "Building wheel for $pkg"
      # use no isolation to leverage existing torch install and avoid strict torch==2.3.0
      # add --no-build-isolation and set PIP_NO_BUILD_ISOLATION to speed up dependency resolution
      export PIP_NO_BUILD_ISOLATION=1
      export PIP_DISABLE_PIP_VERSION_CHECK=1
      (cd "$pkg" && python3 -m build --wheel --no-isolation --outdir "$OLDPWD/$OUTPUT_DIR")
    fi
  done
done

echo "All wheels built and available in $OUTPUT_DIR/"
