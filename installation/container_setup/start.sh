# Build and run the Docker container
# Path to the docker-compose file
DOCKER_COMPOSE_FILE="$(dirname "$0")/docker-compose.yml"

# Build and run the Docker container
docker compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
docker compose -f "$DOCKER_COMPOSE_FILE" up -d

# Display SSH connection information
echo "Docker container is running. You can connect via SSH with:"
echo "ssh root@<remote_server_ip> -p 2222"

# Get the container ID or name dynamically using the service name
#service_name="sage"
#container_name=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q $service_name)

# Wait for the container to start
sleep 5  # Wait to ensure that container is properly up

echo " <ssh root@localhost -p 2222> to access to the docker instance"