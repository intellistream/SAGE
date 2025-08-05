#!/bin/bash

# Check for arguments and provide usage information if not supplied
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <GIT_USERNAME> <GIT_TOKEN>"
  echo "Please provide your GitHub username and personal access token as arguments."
  exit 1
fi

GIT_USERNAME="$1"
GIT_TOKEN="$2"

# URL encode the token (to handle special characters)
ENCODED_TOKEN=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$GIT_TOKEN'''))")

# Navigate to the project root directory
cd "$(dirname "$0")/../.." || exit

# Project root directory
PROJ_DIR=$(pwd)

# Exit immediately if a command exits with a non-zero status
set -e
exec &> >(tee -a "$PROJ_DIR/installation/env_setup/install_dep.log")  # Redirect all output to a log file

echo "Starting runtime script..."
export LDFLAGS="-L/usr/local/cuda-12.5/lib64"

# Step 1: Clone private repository (CANDY)
echo "Cloning CANDY repository..."
cd "$PROJ_DIR/deps"

# Check if the directory exists and is valid
if [ -d "CANDY" ]; then
    echo "CANDY directory already exists. Checking if it's a valid repository..."
    cd CANDY
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        echo "CANDY repository is valid. Skipping clone."
        cd ..
        return 0
    else
        echo "CANDY directory exists but is not a valid Git repository. Removing it."
        cd ..
        rm -rf CANDY
    fi
fi

# Construct the repository URL
REPO_URL="https://${GIT_USERNAME}:${ENCODED_TOKEN}@github.com/intellistream/CANDY.git"
echo "Repository URL: $REPO_URL"

# Clone the repository
if ! git clone "$REPO_URL" CANDY; then
    echo "Error: Failed to clone repository. Removing partial/incomplete directory."
    rm -rf CANDY
    exit 1
fi

echo "CANDY repository cloned successfully."

# Step 2: Build and install CANDY
echo "Building and installing CANDY..."
cd "$PROJ_DIR/deps/CANDY/installation/"
if ! bash candy_build.sh; then
  echo "Error: Failed to build CANDY. Please check the build script and dependencies."
  exit 1
fi

cd "$PROJ_DIR/deps/CANDY/installation/install_pycandy"
if ! bash install_pycandy.sh; then
  echo "Error: Failed to install PyCANDY. Please check the installation script and dependencies."
  exit 1
fi
