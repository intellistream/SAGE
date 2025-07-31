"""
Docker Management Module
========================

Handles Docker container operations and setup.
"""

import subprocess
from typing import Optional
from .base import BaseInstaller


class DockerManager(BaseInstaller):
    """Manages Docker containers and operations."""
    
    def check_docker_installed(self) -> bool:
        """Check if Docker is installed."""
        try:
            self.run_command(['docker', '--version'], capture=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def pull_docker_image(self):
        """Pull Docker image if not exists locally."""
        self.print_step("Checking and pulling SAGE Docker image...")
        docker_image = "intellistream/sage:devel-ubuntu22.04"
        
        try:
            # Check if image exists locally
            result = self.run_command(['docker', 'images', '-q', docker_image], capture=True)
            if not result.stdout.strip():
                self.print_info(f"Docker image {docker_image} not found locally, pulling...")
                self.run_command_with_progress(
                    ['docker', 'pull', docker_image],
                    f"Pulling Docker image {docker_image}"
                )
                self.print_success(f"Docker image {docker_image} pulled successfully")
            else:
                self.print_info(f"Docker image {docker_image} already exists locally")
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to pull Docker image: {e}")
            raise RuntimeError(f"Could not pull Docker image {docker_image}")
    
    def start_docker_container(self):
        """Start Docker container using the start script, reusing existing if possible."""
        # Check if a SAGE container is already running
        existing_container = self.get_docker_container_name()
        if existing_container:
            self.print_info(f"Found existing SAGE Docker container: {existing_container}")
            if self.confirm_action("Reuse existing Docker container?"):
                self.print_success(f"Reusing Docker container '{existing_container}'")
                return existing_container
            else:
                self.print_step("Stopping existing container to create fresh one...")
                try:
                    self.run_command(['docker', 'stop', existing_container], capture=True)
                    self.run_command(['docker', 'rm', existing_container], capture=True)
                    self.print_info("Existing container removed")
                except subprocess.CalledProcessError:
                    self.print_warning("Failed to remove existing container, continuing...")
        
        self.print_step("Starting new Docker container...")
        if self.start_script.exists():
            self.run_command(['bash', str(self.start_script)])
        else:
            self.print_error(f"Start script not found: {self.start_script}")
            raise FileNotFoundError("Docker start script missing")
    
    def get_docker_container_name(self) -> Optional[str]:
        """Get the name of the running SAGE Docker container."""
        try:
            result = self.run_command([
                'docker', 'ps', '--filter', 'ancestor=intellistream/sage:devel-ubuntu22.04',
                '--format', '{{.Names}}'
            ], capture=True)
            
            containers = result.stdout.strip().split('\n')
            return containers[0] if containers and containers[0] else None
        except subprocess.CalledProcessError:
            return None
    
    def install_docker_dependencies(self, container_name: str):
        """Install basic dependencies inside Docker container with caching."""
        self.print_step("Checking dependencies in Docker container...")
        
        try:
            # Check if dependencies are already installed
            result = self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                'dpkg -l | grep -E "(build-essential|cmake|git|swig)" | wc -l'
            ], capture=True, check=False)
            
            installed_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            if installed_count >= 4:  # Expected: build-essential, cmake, git, swig (and their deps)
                self.print_success("Dependencies already installed in Docker container, skipping")
                return
            
            self.print_step("Installing missing dependencies in Docker container...")
            # Install basic system dependencies and tools
            self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                '''
                apt-get update && 
                apt-get install -y --no-install-recommends \
                    build-essential \
                    cmake \
                    git \
                    wget \
                    curl \
                    vim \
                    swig \
                    pkg-config \
                    python3-dev \
                    && apt-get clean \
                    && rm -rf /var/lib/apt/lists/*
                '''
            ])
            self.print_success("Dependencies installed in Docker container")
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install dependencies in container: {e}")
            raise
    
    def setup_docker_conda_environment(self, container_name: str):
        """Setup conda environment inside Docker container with reuse logic."""
        self.print_step("Setting up conda environment in Docker container...")
        
        try:
            # Check if conda environment already exists
            result = self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                f'source /opt/conda/bin/activate && conda env list | grep -E "^{self.conda_env_name}\\s"'
            ], capture=True, check=False)
            
            if result.returncode == 0 and result.stdout.strip():
                self.print_success(f"Conda environment '{self.conda_env_name}' already exists in Docker container")
                
                # Check if it has the right Python version
                version_check = self.run_command([
                    'docker', 'exec', '-i', container_name, 'bash', '-c',
                    f'source /opt/conda/bin/activate && conda activate {self.conda_env_name} && python --version'
                ], capture=True, check=False)
                
                if version_check.returncode == 0:
                    python_version = version_check.stdout.strip()
                    self.print_info(f"Existing environment Python version: {python_version}")
                    if "3.11" in python_version:
                        return  # Environment is good, reuse it
                    else:
                        self.print_warning("Python version mismatch, recreating environment...")
                        # Remove old environment
                        self.run_command([
                            'docker', 'exec', '-i', container_name, 'bash', '-c',
                            f'source /opt/conda/bin/activate && conda env remove -n {self.conda_env_name} -y'
                        ], check=False)
            
            # Create new conda environment with Python 3.11
            self.print_step(f"Creating fresh conda environment '{self.conda_env_name}' with Python 3.11...")
            self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                f'''
                source /opt/conda/bin/activate &&
                conda create -n {self.conda_env_name} python=3.11 -y &&
                conda activate {self.conda_env_name} &&
                pip install --upgrade pip
                '''
            ])
            
            # Install C++ build dependencies for sage_ext
            self.print_step("Installing C++ build dependencies in conda environment...")
            self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                f'''
                source /opt/conda/bin/activate &&
                conda activate {self.conda_env_name} &&
                conda install -c conda-forge pkg-config faiss-cpu cmake pybind11 -y &&
                pip install numpy
                '''
            ])
            self.print_success(f"Conda environment '{self.conda_env_name}' created with C++ dependencies in Docker container")
            
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to setup conda environment in container: {e}")
            raise
    
    def remove_docker_containers(self):
        """Remove SAGE Docker containers and images."""
        self.print_step("Removing SAGE Docker containers and images...")
        try:
            # Stop and remove containers
            result = self.run_command([
                'docker', 'ps', '-q', '--filter', 'ancestor=intellistream/sage:devel-ubuntu22.04'
            ], capture=True, check=False)
            
            if result.stdout.strip():
                container_ids = result.stdout.strip().split('\n')
                self.run_command(['docker', 'stop'] + container_ids)
                self.run_command(['docker', 'rm'] + container_ids)
            
            # Remove stopped containers
            result = self.run_command([
                'docker', 'ps', '-aq', '--filter', 'ancestor=intellistream/sage:devel-ubuntu22.04'
            ], capture=True, check=False)
            
            if result.stdout.strip():
                container_ids = result.stdout.strip().split('\n')
                self.run_command(['docker', 'rm'] + container_ids, check=False)
            
            # Remove image
            self.run_command(['docker', 'rmi', 'intellistream/sage:devel-ubuntu22.04'], 
                           check=False, capture=True)
            
            self.print_success("Docker containers and images removed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_info("Docker not found or no SAGE containers to remove")
