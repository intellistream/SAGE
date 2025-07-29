#!/bin/bash

# Exit immediately if a command fails
set -e

# Variables
new_image_name="intellistream/sage" # Docker Hub repository name
tag="devel-ubuntu22.04"            # Image tag

# Step 3: Push the image to Docker Hub
echo "Logging into Docker Hub..."
if ! docker login; then
    echo "Error: Docker login failed. Please check your credentials."
    exit 1
fi

echo "Pushing image '${new_image_name}:${tag}' to Docker Hub..."
if docker push "${new_image_name}:${tag}"; then
    echo "Image '${new_image_name}:${tag}' pushed to Docker Hub successfully!"
else
    echo "Error: Failed to push image '${new_image_name}:${tag}' to Docker Hub."
    exit 1
fi
