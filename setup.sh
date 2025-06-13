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

function check_huggingface_auth() {
    detect_container || return
    if docker exec -it "$DOCKER_CONTAINER_NAME" huggingface-cli whoami &>/dev/null; then
        HUGGINGFACE_LOGGED_IN=1
    else
        HUGGINGFACE_LOGGED_IN=0
    fi
}

function configure_huggingface_auth() {
    detect_container || return
    echo "===================================================="
    echo "         Configuring Hugging Face Authentication"
    echo "===================================================="
    echo "Hugging Face authentication is required to run the SAGE system."
    echo "Please enter your Hugging Face token to log in."
    echo "You can find or generate your token here: https://huggingface.co/settings/tokens"
    echo "If you want to use huggingface mirror, refer to https://hf-mirror.com/"
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

function configure_huggingface_auth_without_docker() {
    echo "===================================================="
    echo "         Configuring Hugging Face Authentication"
    echo "===================================================="
    echo "Hugging Face authentication is required to run the SAGE system."
    echo "Please enter your Hugging Face token to log in."
    echo "You can find or generate your token here: https://huggingface.co/settings/tokens"
    echo "If you want to use Hugging Face mirror, refer to https://hf-mirror.com/"

    read -sp "Enter your Hugging Face token: " HF_TOKEN
    echo ""

    # 执行登录命令（本地）
    huggingface-cli login --token "$HF_TOKEN"

    # 验证登录状态
    if huggingface-cli whoami &>/dev/null; then
        echo "✅ Hugging Face authentication successful!"
        HUGGINGFACE_LOGGED_IN=1
    else
        echo "❌ Hugging Face authentication failed. Please check your token and try again."
        HUGGINGFACE_LOGGED_IN=0
    fi

    pause
}


function run_debug_main() {
    check_huggingface_auth
    if [ "$HUGGINGFACE_LOGGED_IN" -eq 0 ]; then
        echo "Hugging Face authentication is required to run debug_main.py."
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

function troubleshooting() {
    echo "===================================================="
    echo "         Known Issues and Troubleshooting"
    echo "===================================================="
    echo "1. If the build fails in CLion, add the following CMake options:"
    echo "-DCMAKE_EXE_LINKER_FLAGS='-L/usr/local/cuda/lib64'"
    echo "-DCMAKE_SHARED_LINKER_FLAGS='-L/usr/local/cuda/lib64'"
    echo "2. Ensure Hugging Face authentication is completed before using private models."
    echo "3. If you use HF Mirror, remember to refer to https://hf-mirror.com/ carefully to configure bashrc inside the docker instance"
    echo "3.5. If you use Pycharm, remember to configure HF_ENDPOINT=https://hf-mirror.com in Pycharm's environment variable."
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
    echo "1. Update the Python interpreter to use the Conda environment 'sage'."
    echo "2. Ensure the working directory in your IDE is set to the project root."
    echo "3. Run interactive scripts or tests using the configured environment."
    pause
}


create_sage_env_without_docker() {
    # 检查是否已安装 conda
    if ! command -v conda &> /dev/null; then
        echo "❌ Conda 未安装，请先安装 Miniconda 或 Anaconda"
        return 1
    fi

    # 创建 Python 3.11 环境
    echo "🚀 正在创建名为 'sage' 的 Conda 环境（Python 3.11）..."
    conda create -y -n sage python=3.11

    # 激活环境
    echo "✅ 环境创建成功。要激活它，请运行："
    echo "   conda activate sage"
}



function install_necessary_dependencies() {
    echo "Installing necessary dependencies..."
    # Add commands to install dependencies here
    # Example: sudo apt-get install -y package_name
    apt update
    apt install -y swig cmake build-essential
    echo "Dependencies installed successfully."
}


function minimal_setup() {
    echo "Install necessary dependencies..."
    install_necessary_dependencies 
    echo "Setting up Conda environment without Docker..."
    create_sage_env_without_docker 
    echo "activate the Conda environment with:"
    echo "conda activate sage"
    conda activate sage
    echo "install sage package"
    pip install .
    echo "Hugging Face authentication is required to run the SAGE system."
    configure_huggingface_auth_without_docker 
    echo "Minimal setup completed successfully."
    pause
}

function full_setup() {
    echo "Starting full setup..."
    check_docker_installed 
    start_docker_container
    install_dependencies
    setup_conda_environment
    configure_huggingface_auth
    echo "Full setup completed successfully."
    pause
}

function run_example_scripts() {
    echo "Running example using following command:"
    echo "python app/datastream_rag_pipeline.py"
}
function main_menu() {
    while true; do
        clear
        print_header
        echo "Select an option to proceed:"
        echo "1.Minimal Setup ( Set Up Conda Environment)"
        echo "2.Full Setup (Start Docker Container, Install Dependencies, Set Up Conda Environment)"
        echo "3.Enter Docker Instance "
        echo "4.run example scripts"
        echo "5.IDE Setup Guide (Set Up Conda Environment)"
        echo "6.troubleshooting"
        echo "0.Exit"
        pause
         echo "===================================================="
        read -p "Enter your choice [0-6]: " choice
        case $choice in
            1) minimal_setup ;;
            2) full_setup ;;
            3) enter_docker_instance ;;
            4) run_example_scripts ;;
            5) display_ide_setup ;;
            6) troubleshooting ;;
            0)
                echo "Exiting setup script. Goodbye!"
                exit 0 ;;
            *) echo "Invalid choice. Please try again."; pause ;;
        esac
    done
}

# Start the Interactive Menu
main_menu
