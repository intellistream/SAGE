#!/bin/bash

GIT_USERNAME="$1"
GIT_TOKEN="$2"

# Navigate to the project root directory
cd "$(dirname "$0")/../.." || exit

# Project root directory
PROJ_DIR=$(pwd)

# Exit immediately if a command exits with a non-zero status
set -e
exec &> >(tee -a $PROJ_DIR/installation/env_setup/auto_env_setup.log)  # Redirect all output to a log file

echo "Starting runtime script..."
export LDFLAGS="-L/usr/local/cuda-12.5/lib64"

conda run -n sage bash install_pycandy.sh

# Step 3: Source Conda to activate environment properly
echo "Activating Conda environment..."
conda create -n sage python=3.11 -y
source /opt/conda/bin/activate
conda activate sage

# Step 4: Install Hugging Face dependencies
echo "Installing Hugging Face dependencies..."
pip install torch==2.4.0 huggingface_hub

# Step 5: Update Conda environment with environment.yml
echo "Updating Conda environment with environment.yml..."
conda env update --name sage --file $PROJ_DIR/installation/environment.yml

# Step 6: Install/Update libstdc++ to avoid runtime issues
echo "Installing or updating libstdcxx-ng..."
conda install -n sage -c conda-forge libstdcxx-ng -y