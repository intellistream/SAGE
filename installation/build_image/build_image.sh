#!/bin/bash

# Exit immediately if a command fails
set -e

# Variables
new_image_name="intellistream/sage" # Docker Hub repository name
tag="devel-ubuntu22.04"            # Image tag
dockerfile_dir="./"                # Directory containing the Dockerfile

# Step 1: Build the Docker image
echo "Building the Docker image..."
docker build --no-cache -t "${new_image_name}:${tag}" "${dockerfile_dir}"

# Step 2: Verify the built image
echo "Image built successfully. Verifying the new Docker image..."
docker images | grep "${new_image_name}"