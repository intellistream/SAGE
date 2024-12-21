# Build and run the Docker container
docker-compose down --remove-orphans
docker-compose up -d

# Display SSH connection information
echo "Docker container is running. You can connect via SSH with:"
echo "ssh root@<remote_server_ip> -p 2222"

# Get the container ID or name dynamically using the service name
service_name="sage"
container_name=$(docker-compose ps -q $service_name)

# Wait for the container to start
sleep 5  # Wait to ensure that container is properly up

# Automatically attach to the container's bash shell
docker exec -it $container_name /bin/bash