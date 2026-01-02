#!/bin/bash

echo "First, make sure you have sudo"
sudo ls
echo "Installing others..."
sudo apt-get install -y graphviz
pip install matplotlib pandas==2.0.0
pip install "torch>=1.13.0" --index-url https://download.pytorch.org/whl/cpu
echo "Build LibAMM and PyAMM"
# Step 1: Configure the project
export CUDACXX=/usr/local/cuda/bin/nvcc
mkdir build
cd build &&cmake -DCMAKE_PREFIX_PATH=`python3 -c 'import torch;print(torch.utils.cmake_prefix_path)'` -DENABLE_HDF5=ON -DENABLE_PYBIND=ON -DCMAKE_INSTALL_PREFIX=/usr/local/lib -DENABLE_PAPI=OFF ..

# Step 2: Determine the maximum number of threads
max_threads=$(nproc)

# Step 3: Build the project using the maximum number of threads
cmake --build . --parallel $max_threads
