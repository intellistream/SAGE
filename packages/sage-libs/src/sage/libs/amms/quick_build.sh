#!/bin/bash
# Quick build script for high-memory machines
# Run this on a machine with 64GB+ RAM

set -e

echo "======================================"
echo "isage-amms Quick Build"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Run this script from the amms directory"
    echo "Expected: packages/sage-libs/src/sage/libs/amms/"
    exit 1
fi

# Install build dependencies
echo "Installing build dependencies..."
pip install --upgrade pip setuptools wheel build twine pybind11
pip install torch>=2.0.0 --index-url https://download.pytorch.org/whl/cpu

# Clean
echo ""
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info implementations/build/

# Build
echo ""
echo "Building package..."
python3 -m build --sdist --wheel .

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "Build successful!"
    echo "======================================"
    echo ""
    echo "Built packages:"
    ls -lh dist/
    echo ""
    echo "Next steps:"
    echo "1. Test locally: pip install dist/isage_amms-*.whl"
    echo "2. Upload to TestPyPI: twine upload --repository testpypi dist/*"
    echo "3. Upload to PyPI: twine upload dist/*"
else
    echo ""
    echo "Build failed!"
    exit 1
fi
