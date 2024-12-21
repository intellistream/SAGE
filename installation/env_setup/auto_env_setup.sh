#!/bin/bash

GIT_USERNAME=$1
GIT_TOKEN=$2

# Navigate to the project root directory
cd "$(dirname "$0")/../.." || exit

# Project root directory
PROJ_DIR=$(pwd)

# Exit immediately if a command exits with a non-zero status
set -e
exec &> >(tee -a $PROJ_DIR/installation/env_setup/auto_env_setup.log)  # Redirect all output to a log file

echo "Starting runtime script..."
export LDFLAGS="-L/usr/local/cuda-12.5/lib64"

# Step 1: Clone private repository (CANDY)
echo "Cloning CANDY repository..."
cd $PROJ_DIR/deps
rm -rf CANDY
if [ ! -d "CANDY" ]; then
  git clone https://${GIT_USERNAME}:${GIT_TOKEN}@github.com/intellistream/CANDY.git $PROJ_DIR/deps/CANDY
else
  echo "CANDY repository already exists. Skipping clone."
fi

# Step 2: Build and install CANDY
echo "Building and installing CANDY..."
cd $PROJ_DIR/deps/CANDY/installation/
bash candy_build.sh
cd $PROJ_DIR/deps/CANDY/installation/install_pycandy
conda run -n sage bash install_pycandy.sh

# Step 3: Source Conda to activate environment properly
echo "Activating Conda environment..."
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
