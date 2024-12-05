#!/bin/bash

# Source Conda to activate environment properly
source /opt/conda/bin/activate
conda activate llh

# Install Hugging Face dependencies
pip install torch==2.4.0 huggingface_hub

## Log in to Hugging Face using token from the first argument
#huggingface-cli login --token "$1"

# Update environment and install specific dependencies
conda env update --name llh --file environment.yml
