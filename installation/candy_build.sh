#!/bin/bash

# Navigate to the project root directory
cd "$(dirname "$0")/../.." || exit

# Project root directory
PROJ_DIR=$(pwd)

echo "Building CANDY project in $PROJ_DIR"

# Clean up any previous build directory
if [ -d "$PROJ_DIR/build" ]; then
    echo "Removing existing build directory..."
    rm -rf "$PROJ_DIR/build"
fi

# Create a fresh build directory
mkdir "$PROJ_DIR/build"
cd "$PROJ_DIR/build" || exit

# Run CMake to configure the project
echo "Running CMake configuration..."
cmake ..

# Build the project with parallel jobs
echo "Building the project..."
make -j$(nproc)

# Optionally, install the project (e.g., to Python site-packages if specified in CMakeLists.txt)
echo "Installing the project..."
make install

echo "Build and installation complete."
