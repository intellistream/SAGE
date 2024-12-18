#!/bin/bash

# Exit immediately if a command fails
set -e

# Variables
new_image_name="intellistream/llh" # Docker Hub repository name
tag="devel-ubuntu22.04"            # Image tag
dockerfile_dir="./"                # Directory containing the Dockerfile

# Step 1: Build the Docker image
echo "Building the Docker image..."
docker build --no-cache -t "${new_image_name}:${tag}" "${dockerfile_dir}"

# Step 2: Verify the built image
echo "Image built successfully. Verifying the new Docker image..."
docker images | grep "${new_image_name}"

# # Step 3: Push the image to Docker Hub
# echo "Logging into Docker Hub..."
# if ! docker login; then
#     echo "Error: Docker login failed. Please check your credentials."
#     exit 1
# fi

# echo "Pushing image '${new_image_name}:${tag}' to Docker Hub..."
# if docker push "${new_image_name}:${tag}"; then
#     echo "Image '${new_image_name}:${tag}' pushed to Docker Hub successfully!"
# else
#     echo "Error: Failed to push image '${new_image_name}:${tag}' to Docker Hub."
#     exit 1
# fi
