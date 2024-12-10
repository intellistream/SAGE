#!/bin/bash

# Navigate to the CANDY project directory from the installation folder
cd "$(dirname "$0")/../deps/CANDY" || exit

# CANDY project directory
CANDY_DIR=$(pwd)

echo "Building CANDY project in $CANDY_DIR"

# Clean up any previous build directory
if [ -d "$CANDY_DIR/build" ]; then
    echo "Removing existing build directory..."
    rm -rf "$CANDY_DIR/build"
fi

# Create a fresh build directory
mkdir "$CANDY_DIR/build"
cd "$CANDY_DIR/build" || exit

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
