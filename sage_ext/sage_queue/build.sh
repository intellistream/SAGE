#!/bin/bash
set -e

echo "Building SAGE Queue (now using CMake)..."

# This script is kept for compatibility but now uses CMake
# Pass all arguments to the new CMake build script
exec "$(dirname "$0")/build_cmake.sh" "$@"
