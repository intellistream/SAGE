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

# Directories to scan
ROOTS=("packages" "packages/commercial" "packages/tools")

for root in "${ROOTS[@]}"; do
  [ -d "$root" ] || continue
  for pkg in "$root"/*; do
    [ -d "$pkg" ] || continue
    if [ -f "$pkg/pyproject.toml" ] || [ -f "$pkg/setup.py" ]; then
      echo "Building wheel for $pkg"
      (cd "$pkg" && python3 -m build --wheel --outdir "$OLDPWD/$OUTPUT_DIR")
    fi
  done
done

echo "All wheels built and available in $OUTPUT_DIR/"
