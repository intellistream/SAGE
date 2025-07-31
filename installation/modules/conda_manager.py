"""
Conda Environment Management Module
===================================

Handles conda environment creation and Python package management.
"""

import os
import subprocess
import time
from pathlib import Path
from .base import BaseInstaller


class CondaManager(BaseInstaller):
    """Manages conda environments and Python packages."""
    
    def check_sage_env_exists(self) -> bool:
        """Check if sage conda environment exists."""
        try:
            result = self.run_command(['conda', 'env', 'list'], capture=True)
            env_lines = result.stdout.strip().split('\n')
            for line in env_lines:
                if line.strip().startswith(self.conda_env_name + ' ') or line.strip().startswith(self.conda_env_name + '\t'):
                    return True
            return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def create_conda_environment(self):
        """Create the conda environment."""
        self.print_step(f"Creating conda environment '{self.conda_env_name}'...")
        
        if not self._check_conda_available():
            self.print_error("Conda is not installed. Please install Miniconda or Anaconda first.")
            self.print_info("Download from: https://docs.conda.io/en/latest/miniconda.html")
            raise RuntimeError("Conda not found")
        
        if self.check_sage_env_exists():
            self.print_info(f"Conda environment '{self.conda_env_name}' already exists, skipping creation.")
            return
        
        try:
            self.run_command(['conda', 'create', '-y', '-n', self.conda_env_name, 'python=3.11'])
            self.print_success(f"Conda environment '{self.conda_env_name}' created successfully.")
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to create conda environment: {e}")
            raise
    
    def install_python_packages(self, minimal: bool = True):
        """Install Python packages in the conda environment."""
        self.print_step("Installing Python packages...")
        
        try:
            # Set environment variable for installation
            env = os.environ.copy()
            env['SAGE_INSTALLER_ACTIVE'] = 'true'  # Bypass setup.py guard
            
            if minimal:
                env['SAGE_MINIMAL_INSTALL'] = 'true'
                env['SAGE_QUEUE_BACKEND'] = 'ray'  # Use Ray Queue for minimal install
                self.print_info("Installing SAGE in minimal mode (Python-only)")
            else:
                env['SAGE_MINIMAL_INSTALL'] = 'false'
                env['SAGE_QUEUE_BACKEND'] = 'sage'  # Use native SAGE Queue
                self.print_info("Installing SAGE with C++ extension support")
            
            # Install the main SAGE package with progress
            self.run_command_with_progress(
                ['conda', 'run', '-n', self.conda_env_name, 'pip', 'install', '.'], 
                "Installing SAGE and dependencies",
                env=env
            )
            
            if minimal:
                self.print_success("Python packages installed successfully (minimal mode).")
                self.print_info("C++ extensions skipped for faster installation")
                self.print_info("Using Ray Queue for communication")
            else:
                self.print_success("Python packages installed successfully.")
                
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install Python packages: {e}")
            raise
    
    def setup_huggingface_auth(self):
        """Configure Hugging Face authentication."""
        self.print_header("Hugging Face Authentication")
        
        # Test HF Mirror connectivity
        self.print_step("Testing connectivity to HF Mirror...")
        try:
            import urllib.request
            urllib.request.urlopen('https://hf-mirror.com', timeout=5)
            self.print_success("HF Mirror is accessible")
            hf_endpoint = "https://hf-mirror.com"
        except Exception:
            self.print_warning("HF Mirror is not accessible, using official API")
            hf_endpoint = "https://huggingface.co"
        
        # Set environment variable
        os.environ['HF_ENDPOINT'] = hf_endpoint
        
        # Get token
        if self.is_ci:
            hf_token = os.getenv('HF_TOKEN')
            if not hf_token:
                self.print_error("CI detected but HF_TOKEN is not set.")
                return
        else:
            import getpass
            from .base import Colors
            print(f"{Colors.BLUE}Please enter your Hugging Face token from:")
            print(f"{Colors.BLUE}https://huggingface.co/settings/tokens{Colors.RESET}")
            print(f"{Colors.YELLOW}Note: Your input will be hidden for security.{Colors.RESET}")
            hf_token = getpass.getpass("Token: ")
            
            if not hf_token.strip():
                self.print_info("Skipping Hugging Face authentication.")
                return
        
        try:
            # Login with the token
            env = os.environ.copy()
            env['HF_ENDPOINT'] = hf_endpoint
            
            self.run_command(['conda', 'run', '-n', self.conda_env_name, 'huggingface-cli', 'login', 
                            '--token', hf_token], capture=True)
            
            # Verify login
            self.run_command(['conda', 'run', '-n', self.conda_env_name, 'huggingface-cli', 'whoami'], 
                           capture=True)
            
            self.print_success("Hugging Face authentication successful!")
            
            # Save configuration
            self.config['hf_authenticated'] = True
            self.config['hf_endpoint'] = hf_endpoint
            
        except subprocess.CalledProcessError:
            self.print_error("Hugging Face authentication failed.")
            self.print_info("You can configure this later manually:")
            self.print_info(f"  export HF_ENDPOINT={hf_endpoint}")
            self.print_info(f"  conda activate {self.conda_env_name}")
            self.print_info("  huggingface-cli login --token <your_token>")
    
    def remove_conda_environment(self):
        """Remove the conda environment."""
        self.print_step(f"Removing conda environment '{self.conda_env_name}'...")
        try:
            self.run_command(['conda', 'env', 'remove', '-n', self.conda_env_name, '-y'], capture=True)
            self.print_success("Conda environment removed")
        except subprocess.CalledProcessError:
            self.print_info(f"Conda environment '{self.conda_env_name}' not found or already removed")
    
    def _check_conda_available(self) -> bool:
        """Check if conda is available."""
        try:
            self.run_command(['conda', '--version'], capture=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
