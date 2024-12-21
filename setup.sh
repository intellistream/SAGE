#!/bin/bash

# Interactive Bash Script for SAGE Project Setup
# Dynamically detects the Docker container name and reuses it across functions.

# Variables
DOCKER_COMPOSE_FILE="installation/container_setup/docker-compose.yml"
START_SCRIPT="installation/container_setup/start.sh"
INSTALL_DEP_SCRIPT="installation/env_setup/install_dep.sh"
AUTO_ENV_SETUP_SCRIPT="installation/env_setup/auto_env_setup.sh"
TEST_COMMAND="pytest -v tests/"
DOCKER_CONTAINER_NAME=""  # To be set dynamically

# Functions
function print_header() {
    echo "===================================================="
    echo "            SAGE Project Setup Script"
    echo "===================================================="
}

function pause() {
    read -p "Press [Enter] to return to the main menu..."
}

function detect_container() {
    # Detect the Docker container name dynamically
    if [ -z "$DOCKER_CONTAINER_NAME" ]; then
        DOCKER_CONTAINER_NAME=$(docker ps --filter "ancestor=intellistream/sage:devel-ubuntu22.04" --format "{{.Names}}" | head -n 1)
        if [ -z "$DOCKER_CONTAINER_NAME" ]; then
            echo "Error: No running container found for the specified image."
            echo "Please ensure the Docker container is running before proceeding."
            pause
            return 1
        fi
    fi
    echo "Detected running container: $DOCKER_CONTAINER_NAME"
    return 0
}

function check_docker_installed() {
    echo "Checking if Docker is installed..."
    if ! command -v docker &>/dev/null; then
        echo "Docker is not installed. Please install Docker and try again."
        pause
        return
    fi
    echo "Docker is installed and ready to use."
    pause
}

function start_docker_container() {
    echo "Starting Docker container..."

    # Run the start script to manage Docker container lifecycle
    bash "$START_SCRIPT"

    # Check if the container started successfully
    detect_container || return
    echo "Docker container started successfully."
    echo "You can connect to the container via SSH:"
    echo "ssh root@localhost -p 2222"
    pause
}

function install_dependencies() {
    detect_container || return
    read -p "Enter your GitHub username: " GIT_USERNAME
    read -sp "Enter your GitHub token: " GIT_TOKEN
    echo

    echo "Installing project dependencies inside Docker container..."
    docker exec -it "$DOCKER_CONTAINER_NAME" bash -c "bash /workspace/$INSTALL_DEP_SCRIPT $GIT_USERNAME $GIT_TOKEN"
    echo "Dependencies installed successfully."
    pause
}

function setup_conda_environment() {
    detect_container || return
    echo "Setting up Conda environment in Docker container..."
    docker exec -it "$DOCKER_CONTAINER_NAME" bash -c "bash /workspace/$AUTO_ENV_SETUP_SCRIPT"
    echo "Conda environment set up successfully."
    pause
}

function run_tests() {
    detect_container || return
    echo "Running project tests inside Docker container..."
    docker exec -it "$DOCKER_CONTAINER_NAME" bash -c "bash -c '$TEST_COMMAND'"
    echo "Tests completed successfully."
    pause
}

function troubleshooting() {
    echo "Known Issues and Troubleshooting:"
    echo "1. If build fails in CLion, add the following CMake options:"
    echo "-DCMAKE_EXE_LINKER_FLAGS='-L/usr/local/cuda/lib64'"
    echo "-DCMAKE_SHARED_LINKER_FLAGS='-L/usr/local/cuda/lib64'"
    pause
}

function main_menu() {
    while true; do
        clear
        print_header
        echo "Select an option to proceed:"
        echo "1. Check Docker Installation"
        echo "2. Start Docker Container"
        echo "3. Install Dependencies (GitHub Credentials Required)"
        echo "4. Set Up Conda Environment"
        echo "5. Run Tests"
        echo "6. Troubleshooting Guide"
        echo "0. Exit"
        echo "===================================================="
        read -p "Enter your choice [0-6]: " choice

        case $choice in
            1) check_docker_installed ;;
            2) start_docker_container ;;
            3) install_dependencies ;;
            4) setup_conda_environment ;;
            5) run_tests ;;
            6) troubleshooting ;;
            0) echo "Exiting setup script. Goodbye!"; exit 0 ;;
            *) echo "Invalid choice. Please try again."; pause ;;
        esac
    done
}

# Start the Interactive Menu
main_menu
