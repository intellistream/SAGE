#!/bin/bash
# Clean up build artifacts and temporary files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Cleaning up AMMS build artifacts..."

cd "$SCRIPT_DIR"

# Remove Python build artifacts
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/
rm -rf .eggs/

# Remove C++ build artifacts
rm -rf implementations/build/
rm -rf implementations/dist/
rm -rf implementations/*.egg-info/

# Remove compiled Python files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.so" -delete 2>/dev/null || true

# Remove CMake artifacts
find . -name "CMakeCache.txt" -delete 2>/dev/null || true
find . -type d -name "CMakeFiles" -exec rm -rf {} + 2>/dev/null || true

# Remove temporary files
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name "*.log" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true

echo "Cleanup complete!"
