#!/bin/bash

# Interactive Bash Script for SAGE Project Setup
# Dynamically detects the Docker container name and reuses it across functions.

# Variables
START_SCRIPT="installation/container_setup/start.sh"
INSTALL_DEP_SCRIPT="installation/env_setup/install_dep.sh"
AUTO_ENV_SETUP_SCRIPT="installation/env_setup/auto_env_setup.sh"
DOCKER_CONTAINER_NAME=""  # To be set dynamically
HUGGINGFACE_LOGGED_IN=0  # Track if Hugging Face login is detected

# Functions
function print_header() {
    echo "===================================================="
    echo "            SAGE Project Setup Script"
    echo "===================================================="
}

function pause() {
    read -p "Press [Enter] to continue..."
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
    bash "$START_SCRIPT"
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
    echo ""
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

function configure_huggingface_auth() {
    detect_container || return
    echo "===================================================="
    echo "         Configuring Hugging Face Authentication"
    echo "===================================================="
    echo "Hugging Face authentication is required to run the SAGE system."
    echo "Please enter your Hugging Face token to log in."
    echo "You can find or generate your token here: https://huggingface.co/settings/tokens"
    echo ""
    read -sp "Enter your Hugging Face token: " HF_TOKEN
    echo ""
    docker exec -it "$DOCKER_CONTAINER_NAME" bash -c "huggingface-cli login --token $HF_TOKEN"
    if docker exec -it "$DOCKER_CONTAINER_NAME" huggingface-cli whoami &>/dev/null; then
        echo "Hugging Face authentication successful!"
        HUGGINGFACE_LOGGED_IN=1
    else
        echo "Hugging Face authentication failed. Please check your token and try again."
        HUGGINGFACE_LOGGED_IN=0
    fi
    pause
}

function run_debug_main() {
    check_huggingface_auth
    if [ "$HUGGINGFACE_LOGGED_IN" -eq 0 ]; then
        echo "Hugging Face authentication is required to run debug_main.py."
        echo "Some models may require authentication on the Hugging Face website."
        echo "Please log in using the following command:"
        echo "huggingface-cli login --token <your_huggingface_token>"
        pause
        return
    fi
    detect_container || return
    echo "Running debug_main.py inside Docker container..."
    docker exec -it "$DOCKER_CONTAINER_NAME" bash -c "PYTHONPATH=/workspace conda run -n sage python /workspace/debug_main.py"
    echo "debug_main.py executed successfully."
    pause
}

function enter_docker_instance() {
    detect_container || return
    echo "Opening a terminal inside the Docker container..."
    docker exec -it "$DOCKER_CONTAINER_NAME" bash
}

function display_ide_setup() {
    echo "===================================================="
    echo "            Setting Up SAGE on an IDE"
    echo "===================================================="
    echo "To set up SAGE on an IDE like PyCharm or VS Code:"
    echo ""
    echo "1. Update the Python interpreter to use the Conda environment 'sage'."
    echo "2. Ensure the working directory in your IDE is set to the project root."
    echo "3. Run interactive scripts or tests using the configured environment."
    echo ""
    echo "If you face any issues, log them in our issue tracker."
    echo ""
    pause
}

function troubleshooting() {
    echo "===================================================="
    echo "         Known Issues and Troubleshooting"
    echo "===================================================="
    echo "1. If the build fails in CLion, add the following CMake options:"
    echo "-DCMAKE_EXE_LINKER_FLAGS='-L/usr/local/cuda/lib64'"
    echo "-DCMAKE_SHARED_LINKER_FLAGS='-L/usr/local/cuda/lib64'"
    echo ""
    echo "2. Ensure Hugging Face authentication is completed before using private models."
    echo ""
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
        echo "5. Configure Hugging Face Authentication"
        echo "6. Run debug_main.py"
        echo "7. Enter Docker Instance"
        echo "8. IDE Setup Guide"
        echo "9. Troubleshooting Guide"
        echo "0. Exit"
        echo "===================================================="
        read -p "Enter your choice [0-9]: " choice
        case $choice in
            1) check_docker_installed ;;
            2) start_docker_container ;;
            3) install_dependencies ;;
            4) setup_conda_environment ;;
            5) configure_huggingface_auth ;;
            6) run_debug_main ;;
            7) enter_docker_instance ;;
            8) display_ide_setup ;;
            9) troubleshooting ;;
            0)
                echo "Exiting setup script. Goodbye!"
                exit 0 ;;
            *) echo "Invalid choice. Please try again."; pause ;;
        esac
    done
}

# Start the Interactive Menu
main_menu
