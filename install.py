#!/usr/bin/env python3
"""
SAGE Framework Installation Script
==================================

Professional installation and management tool for the SAGE framework.
Supports both minimal (Python-only) and full (Docker + C++) installations.

Usage:
    python install.py              # Interactive menu
    python install.py --minimal    # Direct minimal installation
    python install.py --full       # Direct full installation
    python install.py --uninstall  # Direct uninstallation
    python install.py --help       # Show help
"""

import os
import sys
import subprocess
import shutil
import argparse
import json
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

class SageInstaller:
    """Main SAGE installation and management class."""
    
    def __init__(self):
        self.sage_dir = Path.home() / ".sage_setup"
        self.sage_dir.mkdir(exist_ok=True)
        self.config_file = self.sage_dir / "config.json"
        self.project_root = Path.cwd()
        self.is_ci = os.getenv('CI', '').lower() in ('true', '1', 'yes')
        
        # Load existing configuration
        self.config = self.load_config()
        
        # Installation paths
        self.requirements_file = self.project_root / "installation" / "env_setup" / "requirements.txt"
        self.start_script = self.project_root / "installation" / "container_setup" / "start.sh"
        self.install_dep_script = self.project_root / "installation" / "env_setup" / "install_dep.sh"
        self.auto_env_setup_script = self.project_root / "installation" / "env_setup" / "auto_env_setup.sh"
        
        # Register cleanup function
        import atexit
        atexit.register(self._cleanup_temp_files)
    
    def _cleanup_temp_files(self):
        """Clean up temporary files created during installation."""
        temp_script = self.project_root / ".sage_temp_activate.sh"
        if temp_script.exists():
            try:
                temp_script.unlink()
            except:
                pass  # Ignore cleanup errors
        
    def load_config(self) -> Dict:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            self.print_error(f"Failed to save configuration: {e}")
    
    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")
    
    def print_success(self, text: str):
        """Print success message."""
        print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")
    
    def print_error(self, text: str):
        """Print error message."""
        print(f"{Colors.RED}❌ {text}{Colors.RESET}")
    
    def print_warning(self, text: str):
        """Print warning message."""
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")
    
    def print_info(self, text: str):
        """Print info message."""
        print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")
    
    def print_step(self, text: str):
        """Print step message."""
        print(f"{Colors.MAGENTA}🔧 {text}{Colors.RESET}")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, check: bool = True, 
                   capture: bool = False, env: Optional[Dict] = None) -> subprocess.CompletedProcess:
        """Run a shell command with proper error handling."""
        try:
            if capture:
                result = subprocess.run(cmd, cwd=cwd, check=check, 
                                      capture_output=True, text=True, env=env)
            else:
                result = subprocess.run(cmd, cwd=cwd, check=check, env=env)
            return result
        except subprocess.CalledProcessError as e:
            if capture and e.stderr:
                self.print_error(f"Command failed: {' '.join(cmd)}")
                self.print_error(f"Error: {e.stderr.strip()}")
            raise
        except FileNotFoundError:
            self.print_error(f"Command not found: {cmd[0]}")
            raise
    
    def check_conda_installed(self) -> bool:
        """Check if conda is installed."""
        try:
            self.run_command(['conda', '--version'], capture=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_docker_installed(self) -> bool:
        """Check if Docker is installed."""
        try:
            self.run_command(['docker', '--version'], capture=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_sage_env_exists(self) -> bool:
        """Check if sage conda environment exists."""
        try:
            result = self.run_command(['conda', 'env', 'list'], capture=True)
            return 'sage' in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def pause(self):
        """Pause for user input (skip in CI)."""
        if not self.is_ci:
            input(f"{Colors.CYAN}Press [Enter] to continue...{Colors.RESET}")
    
    def get_user_input(self, prompt: str, default: str = "") -> str:
        """Get user input with optional default."""
        if self.is_ci:
            return default
        try:
            response = input(f"{Colors.YELLOW}{prompt}{Colors.RESET}")
            return response.strip() if response.strip() else default
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Installation cancelled by user.{Colors.RESET}")
            sys.exit(0)
    
    def confirm_action(self, prompt: str) -> bool:
        """Ask for user confirmation."""
        if self.is_ci:
            return True
        response = self.get_user_input(f"{prompt} (y/N): ", "n")
        return response.lower() in ('y', 'yes')
    
    def install_system_dependencies(self):
        """Install system dependencies for minimal setup."""
        self.print_step("Installing system dependencies...")
        
        deps_marker = self.sage_dir / "deps_installed"
        if deps_marker.exists():
            self.print_info("System dependencies already installed, skipping.")
            return
        
        # Detect package manager
        if platform.system() == "Linux":
            try:
                # Try apt-get (Ubuntu/Debian)
                if shutil.which('apt-get'):
                    if os.geteuid() != 0:  # Not root
                        cmd_prefix = ['sudo']
                    else:
                        cmd_prefix = []
                    
                    self.run_command(cmd_prefix + ['apt-get', 'update', '-y'])
                    self.run_command(cmd_prefix + ['apt-get', 'install', '-y', 
                                                 '--no-install-recommends',
                                                 'swig', 'cmake', 'build-essential'])
                    deps_marker.touch()
                    self.print_success("System dependencies installed successfully.")
                else:
                    self.print_warning("apt-get not found. Please install swig, cmake, and build-essential manually.")
            except subprocess.CalledProcessError as e:
                self.print_error(f"Failed to install system dependencies: {e}")
                raise
        else:
            self.print_warning(f"System dependency installation not supported on {platform.system()}.")
            self.print_info("Please ensure you have the following installed: swig, cmake, build tools")
    
    def create_conda_environment(self):
        """Create the sage conda environment."""
        self.print_step("Creating conda environment 'sage'...")
        
        if not self.check_conda_installed():
            self.print_error("Conda is not installed. Please install Miniconda or Anaconda first.")
            self.print_info("Download from: https://docs.conda.io/en/latest/miniconda.html")
            raise RuntimeError("Conda not found")
        
        if self.check_sage_env_exists():
            self.print_info("Conda environment 'sage' already exists, skipping creation.")
            return
        
        try:
            self.run_command(['conda', 'create', '-y', '-n', 'sage', 'python=3.11'])
            self.print_success("Conda environment 'sage' created successfully.")
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to create conda environment: {e}")
            raise
    
    def install_python_packages(self):
        """Install Python packages in the sage environment."""
        self.print_step("Installing Python packages...")
        
        try:
            # Set environment variable for minimal installation and installer detection
            env = os.environ.copy()
            env['SAGE_MINIMAL_INSTALL'] = 'true'
            env['SAGE_INSTALLER_ACTIVE'] = 'true'  # Bypass setup.py guard
            env['SAGE_QUEUE_BACKEND'] = 'ray'  # Use Ray Queue for minimal install
            
            # Install the main SAGE package (minimal mode - no C++ extensions)
            self.run_command(['conda', 'run', '-n', 'sage', 'pip', 'install', '.'], 
                           env=env)
            
            self.print_success("Python packages installed successfully (minimal mode).")
            self.print_info("C++ extensions skipped for faster installation")
            self.print_info("Using Ray Queue for communication (no high-performance SageQueue)")
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install Python packages: {e}")
            raise
    
    def build_sage_ext_libraries(self):
        """Build all C++ libraries found in sage_ext directory using build.sh scripts."""
        self.print_step("Building SAGE extension libraries...")
        
        sage_ext_dir = self.project_root / "sage_ext"
        if not sage_ext_dir.exists():
            self.print_warning("sage_ext directory not found, skipping extension builds")
            return False
        
        built_any = False
        failed_builds = []
        
        # Find all build.sh scripts in sage_ext subdirectories
        for build_script in sage_ext_dir.rglob("build.sh"):
            extension_dir = build_script.parent
            extension_name = extension_dir.name
            
            self.print_info(f"Building extension: {extension_name}")
            
            try:
                # Make sure build script is executable
                build_script.chmod(0o755)
                
                # Run the build script
                result = self.run_command(
                    ['bash', str(build_script)], 
                    cwd=extension_dir,
                    capture=True,
                    check=False
                )
                
                if result.returncode == 0:
                    self.print_success(f"✅ {extension_name} built successfully")
                    if result.stdout:
                        print(f"   Output: {result.stdout.strip()}")
                    built_any = True
                else:
                    self.print_error(f"❌ {extension_name} build failed")
                    if result.stderr:
                        print(f"   Error: {result.stderr.strip()}")
                    failed_builds.append(extension_name)
                    
            except Exception as e:
                self.print_error(f"❌ Exception building {extension_name}: {e}")
                failed_builds.append(extension_name)
        
        if built_any:
            self.print_success("Extension libraries built successfully")
        
        if failed_builds:
            self.print_warning(f"Failed to build extensions: {', '.join(failed_builds)}")
            return False
            
        return built_any

    def install_python_packages_with_cpp(self):
        """Install Python packages with C++ extensions in the sage environment."""
        self.print_step("Installing Python packages with C++ extensions...")
        
        try:
            # First, build all sage_ext C++ libraries
            extensions_built = self.build_sage_ext_libraries()
            
            # Set environment variables for full installation
            env = os.environ.copy()
            env['SAGE_MINIMAL_INSTALL'] = 'false'
            env['SAGE_INSTALLER_ACTIVE'] = 'true'  # Bypass setup.py guard
            env['SAGE_QUEUE_BACKEND'] = 'sage' if extensions_built else 'ray'  # Use SageQueue if extensions built
            
            # Install the main SAGE package (full mode - with C++ extensions)
            self.run_command(['conda', 'run', '-n', 'sage', 'pip', 'install', '.'], 
                           env=env)
            
            # Try to build extensions using the extension manager
            try:
                self.print_step("Building C++ extensions via extension manager...")
                self.run_command([
                    'conda', 'run', '-n', 'sage', 'python', '-c',
                    'from sage_ext import get_extension_manager; '
                    'print("Extensions built:" if get_extension_manager().build_all_extensions() else "Extensions failed")'
                ])
                
                self.print_success("C++ extensions built successfully")
                    
            except Exception as e:
                self.print_warning(f"Extension manager build error: {e}")
                if not extensions_built:
                    self.print_warning("Falling back to Ray Queue")
                    env['SAGE_QUEUE_BACKEND'] = 'ray'
            
            self.print_success("Python packages installed successfully (full mode).")
            
            backend = env.get('SAGE_QUEUE_BACKEND', 'ray')
            if backend == 'sage':
                self.print_info("Using high-performance SageQueue with C++ extensions")
            else:
                self.print_info("Using Ray Queue (C++ extensions not available)")
                
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
                raise RuntimeError("HF_TOKEN required in CI environment")
        else:
            print(f"{Colors.BLUE}Please enter your Hugging Face token from:")
            print(f"{Colors.BLUE}https://huggingface.co/settings/tokens{Colors.RESET}")
            print(f"{Colors.YELLOW}Note: Your input will be hidden for security.{Colors.RESET}")
            
            import getpass
            hf_token = getpass.getpass("Token: ")
            
            if not hf_token.strip():
                self.print_info("Skipping Hugging Face authentication.")
                return
        
        try:
            # Login with the token
            env = os.environ.copy()
            env['HF_ENDPOINT'] = hf_endpoint
            
            self.run_command(['conda', 'run', '-n', 'sage', 'huggingface-cli', 'login', 
                            '--token', hf_token], capture=True)
            
            # Verify login
            self.run_command(['conda', 'run', '-n', 'sage', 'huggingface-cli', 'whoami'], 
                           capture=True)
            
            self.print_success("Hugging Face authentication successful!")
            
            # Save configuration
            self.config['hf_authenticated'] = True
            self.config['hf_endpoint'] = hf_endpoint
            
        except subprocess.CalledProcessError:
            self.print_error("Hugging Face authentication failed.")
            self.print_info("You can configure this later manually:")
            self.print_info(f"  export HF_ENDPOINT={hf_endpoint}")
            self.print_info("  conda activate sage")
            self.print_info("  huggingface-cli login --token <your_token>")
    
    def minimal_setup(self):
        """Perform minimal Python-only installation."""
        self.print_header("SAGE Minimal Setup")
        print(f"{Colors.YELLOW}⚠️  Python-only installation (no C++ extensions)")
        print(f"{Colors.WHITE}   - Faster installation and setup")
        print(f"{Colors.WHITE}   - Pure Python implementation")
        print(f"{Colors.WHITE}   - Suitable for development and testing{Colors.RESET}\n")
        
        try:
            self.install_system_dependencies()
            self.create_conda_environment()
            self.install_python_packages()
            
            # Optional HF authentication
            if not self.is_ci:
                configure_hf = self.confirm_action("Configure Hugging Face authentication now?")
                if configure_hf:
                    self.setup_huggingface_auth()
            
            # Save configuration
            self.config['setup_type'] = 'minimal'
            self.config['installation_date'] = time.time()
            self.save_config()
            
            # Success message with activation instructions
            self.print_header("Installation Complete!")
            self.print_success("Minimal setup completed successfully!")
            print()
            print(f"{Colors.BLUE}� Note: This version uses pure Python (no C++ extensions){Colors.RESET}")
            print(f"{Colors.GREEN}🚀 Automatically activating SAGE environment...{Colors.RESET}")
            print()
            
            # Create activation script for future use
            self.create_activation_script('minimal')
            
            # Auto-activate the environment if not in CI
            if not self.is_ci:
                self.print_success("🚀 Automatically activating SAGE environment...")
                print(f"{Colors.GREEN}✅ You will now be dropped into the SAGE conda environment{Colors.RESET}")
                print(f"{Colors.BLUE}📝 Your prompt will show (sage) when active{Colors.RESET}")
                print(f"{Colors.YELLOW}💡 To exit the environment later, type: conda deactivate{Colors.RESET}")
                print(f"{Colors.YELLOW}💡 To reactivate later, use: ./activate_sage.sh{Colors.RESET}")
                print()
                
                # Test import before activation
                try:
                    self.run_command(['conda', 'run', '-n', 'sage', 'python', '-c', 'import sage; print("SAGE import test: OK")'], capture=True)
                    test_passed = True
                except:
                    test_passed = False
                
                if test_passed:
                    print(f"{Colors.GREEN}🎉 SAGE is ready!{Colors.RESET}")
                    print()
                    print(f"{Colors.YELLOW}📝 The installer is complete. To activate SAGE:{Colors.RESET}")
                    print(f"{Colors.GREEN}   source ./activate_sage.sh{Colors.RESET}")
                    print(f"{Colors.BLUE}   (Note: Use 'source' not './' - this activates conda in your current shell){Colors.RESET}")
                    print()
                    print(f"{Colors.BLUE}ℹ️  This will give you an activated SAGE environment with (sage) in your prompt{Colors.RESET}")
                    print(f"{Colors.YELLOW}� Alternative: conda activate sage{Colors.RESET}")
                    print()
                    
                    # Ask user if they want to auto-activate now
                    if self.confirm_action("Activate SAGE environment now?"):
                        print(f"{Colors.GREEN}� Activating SAGE environment...{Colors.RESET}")
                        print(f"{Colors.YELLOW}📝 You'll get a new shell with (sage) environment active{Colors.RESET}")
                        print(f"{Colors.YELLOW}📝 Type 'exit' to return to your original shell{Colors.RESET}")
                        print()
                        
                        # Use os.execv to replace current process with activation script
                        import os
                        activation_script = self.project_root / "activate_sage.sh"
                        os.execv('/bin/bash', ['bash', str(activation_script)])
                    else:
                        print(f"{Colors.BLUE}💡 Run ./activate_sage.sh when ready to use SAGE{Colors.RESET}")
                    
                else:
                    self.print_warning("SAGE import test failed. Please check installation.")
                    self.print_info("You can manually activate with: conda activate sage")
            else:
                self.print_info("CI mode: Environment ready for activation with 'conda activate sage'")
            
        except Exception as e:
            self.print_error(f"Minimal setup failed: {e}")
            raise
    
    def full_setup(self):
        """Perform full installation with Docker and C++ extensions."""
        self.print_header("SAGE Full Setup")
        print(f"{Colors.GREEN}✅ Complete installation with Docker and C++ extensions:")
        print(f"{Colors.WHITE}   - Docker container environment")
        print(f"{Colors.WHITE}   - High-performance C++ extensions") 
        print(f"{Colors.WHITE}   - CANDY vector database")
        print(f"{Colors.WHITE}   - Production-ready configuration{Colors.RESET}\n")
        
        # Check Docker
        if not self.check_docker_installed():
            self.print_error("Docker is not installed. Please install Docker and try again.")
            self.print_info("Download from: https://docs.docker.com/get-docker/")
            raise RuntimeError("Docker not found")
        
        try:
            # Start Docker container
            self.print_step("Starting Docker container...")
            if self.start_script.exists():
                self.run_command(['bash', str(self.start_script)])
            else:
                self.print_error(f"Start script not found: {self.start_script}")
                raise FileNotFoundError("Docker start script missing")
            
            # Get container name
            container_name = self.get_docker_container_name()
            if not container_name:
                self.print_error("Failed to detect running Docker container")
                raise RuntimeError("No Docker container found")
            
            self.print_success(f"Docker container '{container_name}' is running")
            
            # Install dependencies in Docker
            self.install_docker_dependencies(container_name)
            
            # Setup conda environment in Docker
            self.setup_docker_conda_environment(container_name)
            
            # Install SAGE with C++ extensions
            self.install_sage_with_cpp(container_name)
            
            # Configure HF auth
            if not self.is_ci:
                configure_hf = self.confirm_action("Configure Hugging Face authentication now?")
                if configure_hf:
                    self.setup_docker_huggingface_auth(container_name)
            
            # Save configuration
            self.config['setup_type'] = 'full'
            self.config['docker_container'] = container_name
            self.config['installation_date'] = time.time()
            self.save_config()
            
            # Success message
            self.print_header("Installation Complete!")
            self.print_success("Full setup completed successfully!")
            print()
            print(f"{Colors.BOLD}🐳 TO ACCESS THE DOCKER ENVIRONMENT:{Colors.RESET}")
            print(f"{Colors.GREEN}   ssh root@localhost -p 2222{Colors.RESET}")
            print(f"{Colors.GREEN}   OR: docker exec -it {container_name} bash{Colors.RESET}")
            print()
            print(f"{Colors.BOLD}🔧 ONCE IN DOCKER, ACTIVATE SAGE ENVIRONMENT:{Colors.RESET}")
            print(f"{Colors.GREEN}   conda activate sage{Colors.RESET}")
            print()
            print(f"{Colors.BLUE}📝 You'll then see (sage) in your prompt{Colors.RESET}")
            print(f"{Colors.GREEN}🚀 C++ extensions and all features available{Colors.RESET}")
            print()
            print(f"{Colors.BOLD}🚀 Quick test after activation:{Colors.RESET}")
            print(f"{Colors.GREEN}   python -c \"import sage; print('SAGE with C++ extensions ready!'){Colors.RESET}")
            print()
            
            # Create activation script
            self.create_activation_script('full', container_name)
            
        except Exception as e:
            self.print_error(f"Full setup failed: {e}")
            raise
    
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
        """Install dependencies inside Docker container."""
        self.print_step("Installing dependencies in Docker container...")
        
        if not self.is_ci:
            git_username = self.get_user_input("Enter your GitHub username: ")
            git_token = self.get_user_input("Enter your GitHub token: ")
        else:
            git_username = os.getenv('GITHUB_USERNAME', 'ci-user')
            git_token = os.getenv('GITHUB_TOKEN', '')
        
        if self.install_dep_script.exists():
            self.run_command([
                'docker', 'exec', '-it', container_name, 'bash', '-c',
                f'bash /workspace/{self.install_dep_script.relative_to(self.project_root)} {git_username} {git_token}'
            ])
            self.print_success("Dependencies installed in Docker container")
        else:
            self.print_warning(f"Install dependencies script not found: {self.install_dep_script}")
    
    def setup_docker_conda_environment(self, container_name: str):
        """Setup conda environment inside Docker container."""
        self.print_step("Setting up conda environment in Docker container...")
        
        if self.auto_env_setup_script.exists():
            self.run_command([
                'docker', 'exec', '-it', container_name, 'bash', '-c',
                f'bash /workspace/{self.auto_env_setup_script.relative_to(self.project_root)}'
            ])
            self.print_success("Conda environment setup in Docker container")
        else:
            self.print_warning(f"Auto env setup script not found: {self.auto_env_setup_script}")
    
    def install_sage_with_cpp(self, container_name: str):
        """Install SAGE with C++ extensions in Docker container."""
        self.print_step("Installing SAGE with C++ extensions...")
        
        # Build C++ extensions using the new extension system
        self.print_step("Building sage_ext C++ libraries in Docker...")
        try:
            # Build all sage_ext libraries using build.sh scripts
            self.run_command([
                'docker', 'exec', '-it', container_name, 'bash', '-c',
                '''cd /workspace && find sage_ext -name "build.sh" -type f | while read build_script; do
                    echo "Building extension: $(dirname "$build_script")"
                    chmod +x "$build_script"
                    cd "$(dirname "$build_script")" && bash "./$(basename "$build_script")" && cd /workspace
                done'''
            ])
            
            self.print_success("sage_ext libraries built successfully")
            extensions_built = True
            
        except subprocess.CalledProcessError as e:
            self.print_warning("sage_ext libraries build failed")
            extensions_built = False
        
        try:
            # Install SAGE with appropriate backend based on extension build success
            backend = 'sage' if extensions_built else 'ray'
            self.run_command([
                'docker', 'exec', '-it', container_name, 'bash', '-c',
                f'cd /workspace && SAGE_MINIMAL_INSTALL=false SAGE_INSTALLER_ACTIVE=true SAGE_QUEUE_BACKEND={backend} conda run -n sage pip install .'
            ])
            
            # Then build extensions using the extension manager
            self.print_step("Building C++ extensions via extension manager...")
            self.run_command([
                'docker', 'exec', '-it', container_name, 'bash', '-c',
                'cd /workspace && conda run -n sage python -c "from sage_ext import get_extension_manager; manager = get_extension_manager(); results = manager.build_all_extensions(); print(f\'Build results: {results}\')"'
            ])
            
            self.print_success("SAGE package installed with C++ extensions")
            
        except subprocess.CalledProcessError as e:
            self.print_warning("C++ extensions build failed, installing with Ray Queue fallback")
            # Fallback installation with Ray backend
            self.run_command([
                'docker', 'exec', '-it', container_name, 'bash', '-c',
                'cd /workspace && SAGE_MINIMAL_INSTALL=true SAGE_INSTALLER_ACTIVE=true SAGE_QUEUE_BACKEND=ray conda run -n sage pip install . --force-reinstall'
            ])
        
        # Verify installation and queue backend
        self.print_step("Verifying installation...")
        try:
            result = self.run_command([
                'docker', 'exec', '-it', container_name, 'bash', '-c',
                'cd /workspace && conda run -n sage python -c "from sage.utils.queue_adapter import get_queue_backend_info; info = get_queue_backend_info(); print(f\'Backend: {info[\"current_backend\"]}, Extensions: {info[\"sage_available\"]}\'); "'
            ])
            self.print_success("Installation verification successful")
        except subprocess.CalledProcessError:
            self.print_warning("Installation verification failed, but continuing")
    
    def setup_docker_huggingface_auth(self, container_name: str):
        """Setup Hugging Face authentication in Docker container."""
        self.print_step("Configuring Hugging Face authentication in Docker...")
        
        hf_endpoint = "https://hf-mirror.com"
        
        if self.is_ci:
            hf_token = os.getenv('HF_TOKEN')
            if not hf_token:
                self.print_error("CI detected but HF_TOKEN is not set.")
                return
        else:
            import getpass
            hf_token = getpass.getpass("Hugging Face Token: ")
            if not hf_token.strip():
                self.print_info("Skipping Hugging Face authentication.")
                return
        
        try:
            self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                f'HF_ENDPOINT={hf_endpoint} huggingface-cli login --token "{hf_token}"'
            ])
            self.print_success("Hugging Face authentication configured in Docker")
        except subprocess.CalledProcessError:
            self.print_error("Failed to configure Hugging Face authentication in Docker")
    
    def create_activation_script(self, setup_type: str, container_name: str = None):
        """Create a convenience activation script."""
        if setup_type == 'minimal':
            script_content = f"""#!/bin/bash
# SAGE Environment Activation Script (Minimal Setup)
# Generated by SAGE installer

echo "🔧 Activating SAGE conda environment..."

# Initialize conda if not already initialized
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found in PATH"
    echo "💡 Please ensure conda is installed and in your PATH"
    exit 1
fi

# Initialize conda for this shell session
eval "$(conda shell.bash hook)" 2>/dev/null || {{
    echo "🔧 Initializing conda for bash..."
    conda init bash
    echo "📝 Conda initialized. Please restart your shell or run 'source ~/.bashrc'"
    echo "📝 Then run this script again: ./activate_sage.sh"
    exit 0
}}

# Activate the sage environment
conda activate sage

if [ $? -eq 0 ]; then
    echo "✅ SAGE environment activated successfully!"
    echo "📝 You are now in the (sage) environment"
    echo "🚀 Test with: python -c \\"import sage; print('SAGE ready!')\""
else
    echo "❌ Failed to activate SAGE environment"
    echo "💡 Try: conda env list"
fi
"""
        else:  # full setup
            script_content = f"""#!/bin/bash
# SAGE Environment Activation Script (Full Setup)
# Generated by SAGE installer

echo "🐳 Connecting to SAGE Docker container..."
echo "Container: {container_name or '<auto-detect>'}"

if command -v docker &> /dev/null; then
    CONTAINER_NAME="{container_name or '$(docker ps --filter "ancestor=intellistream/sage:devel-ubuntu22.04" --format "{{.Names}}" | head -n 1)'}"
    
    if [ -n "$CONTAINER_NAME" ]; then
        echo "✅ Connecting to container: $CONTAINER_NAME"
        echo "🔧 Activating SAGE environment in Docker..."
        docker exec -it "$CONTAINER_NAME" bash -c "conda activate sage && bash"
    else
        echo "❌ No SAGE Docker container found"
        echo "💡 Try: docker ps"
        echo "💡 Or: ssh root@localhost -p 2222"
    fi
else
    echo "❌ Docker not found"
    echo "💡 Alternative: ssh root@localhost -p 2222"
fi
"""
        
        # Write activation script
        script_path = self.project_root / "activate_sage.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        script_path.chmod(0o755)
        
        self.print_info(f"Created activation script: {script_path}")
        self.print_info(f"Run: source ./activate_sage.sh  (Note: use 'source', not './')")
    
    def uninstall_sage(self):
        """Complete uninstallation of SAGE."""
        self.print_header("SAGE Uninstallation")
        print("This will completely remove:")
        print("1. SAGE Python package from all environments")
        print("2. SAGE Conda environment")
        print("3. Docker containers and images")
        print("4. Setup markers and build artifacts")
        print("5. Hugging Face cache (optional)")
        print()
        
        if not self.confirm_action("Are you sure you want to proceed with complete removal?"):
            self.print_info("Uninstallation cancelled.")
            return
        
        try:
            # Remove conda environment
            self.print_step("Removing conda environment 'sage'...")
            try:
                self.run_command(['conda', 'env', 'remove', '-n', 'sage', '-y'], capture=True)
                self.print_success("Conda environment removed")
            except subprocess.CalledProcessError:
                self.print_info("Conda environment 'sage' not found or already removed")
            
            # Remove Docker containers and images
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
            
            # Clean up build artifacts
            self.print_step("Cleaning up build artifacts...")
            
            # Remove setup directory
            if self.sage_dir.exists():
                shutil.rmtree(self.sage_dir)
                self.print_success("Setup markers removed")
            
            # Remove build directories
            for build_dir in ['build', 'sage.egg-info']:
                build_path = self.project_root / build_dir
                if build_path.exists():
                    shutil.rmtree(build_path)
                    self.print_success(f"Removed {build_dir} directory")
            
            # Remove compiled C extensions
            cpp_so_file = self.project_root / "sage" / "utils" / "mmap_queue" / "ring_buffer.so"
            if cpp_so_file.exists():
                cpp_so_file.unlink()
                self.print_success("Removed compiled C extensions")
            
            # Remove Python cache
            for cache_dir in self.project_root.rglob("__pycache__"):
                if cache_dir.is_dir():
                    shutil.rmtree(cache_dir)
            
            for pyc_file in self.project_root.rglob("*.pyc"):
                pyc_file.unlink()
            
            self.print_success("Cleaned Python cache files")
            
            # Remove activation script
            activation_script = self.project_root / "activate_sage.sh"
            if activation_script.exists():
                activation_script.unlink()
                self.print_success("Removed activation script")
            
            # Optional: Clean up Hugging Face cache
            if self.confirm_action("Remove Hugging Face cache and tokens?"):
                hf_cache_dir = Path.home() / ".cache" / "huggingface"
                if hf_cache_dir.exists():
                    if self.confirm_action("Remove Hugging Face model cache? This may be large"):
                        shutil.rmtree(hf_cache_dir)
                        self.print_success("Removed Hugging Face cache")
                    else:
                        # Just remove token
                        hf_token_file = hf_cache_dir / "token"
                        if hf_token_file.exists():
                            hf_token_file.unlink()
                            self.print_success("Removed Hugging Face token")
            
            self.print_header("Uninstallation Complete!")
            self.print_success("SAGE completely uninstalled!")
            self.print_success("Environment reset to clean state")
            
        except Exception as e:
            self.print_error(f"Uninstallation failed: {e}")
            raise
    
    def install_third_party(self):
        """Install third-party components like Kafka."""
        self.print_header("Third-party Components")
        print("Available optional components:")
        print(f"{Colors.BLUE}ℹ️  Note: Core dependencies (CANDY, Docker) are installed in Full Setup{Colors.RESET}")
        print()
        print("1. Kafka (Streaming features)")
        print("2. Back to main menu")
        print()
        
        choice = self.get_user_input("Enter your choice [1-2]: ", "2")
        
        if choice == "1":
            self.print_step("Installing Kafka for streaming features...")
            kafka_install_script = self.project_root / "installation" / "kafka_setup" / "install_kafka.sh"
            
            if kafka_install_script.exists():
                self.run_command(['bash', str(kafka_install_script)])
                self.print_success("Kafka installation completed.")
            else:
                self.print_error("Kafka installation script not found.")
        elif choice == "2":
            return
        else:
            self.print_error("Invalid choice.")
    
    def run_example_scripts(self):
        """Run example scripts to test the installation."""
        self.print_header("Run Example Scripts")
        
        # Check if SAGE is installed
        setup_type = self.config.get('setup_type')
        if not setup_type:
            self.print_error("No SAGE installation detected.")
            self.print_info("Please run Minimal Setup or Full Setup first.")
            return
        
        print("Available examples:")
        print()
        print("1. Basic RAG Pipeline (app/qa_openai.py)")
        print("2. Memory Management Demo")
        print("3. Dataflow Pipeline Example")
        print("4. Back to main menu")
        print()
        
        choice = self.get_user_input("Enter your choice [1-4]: ", "4")
        
        if choice == "1":
            self.print_step("Running basic RAG pipeline example...")
            self._run_example_script("app/qa_openai.py")
        elif choice == "2":
            self.print_step("Running memory management demo...")
            if setup_type == "full":
                container_name = self.config.get('docker_container')
                if container_name:
                    self.run_command([
                        'docker', 'exec', '-it', container_name, 'bash', '-c',
                        'cd /workspace && conda run -n sage python -c "from sage.lib.memory import MemoryManager; print(\\"Memory demo completed\\")"'
                    ])
            else:
                self.run_command([
                    'conda', 'run', '-n', 'sage', 'python', '-c',
                    'from sage.lib.memory import MemoryManager; print("Memory demo completed")'
                ])
        elif choice == "3":
            self.print_step("Running dataflow pipeline example...")
            self._run_example_script("app/datastream_rag_pipeline.py")
        elif choice == "4":
            return
        else:
            self.print_error("Invalid choice.")
    
    def _run_example_script(self, script_path: str):
        """Helper to run an example script."""
        setup_type = self.config.get('setup_type')
        script_file = self.project_root / script_path
        
        if setup_type == "full":
            container_name = self.config.get('docker_container')
            if container_name:
                self.run_command([
                    'docker', 'exec', '-it', container_name, 'bash', '-c',
                    f'cd /workspace && conda run -n sage python {script_path}'
                ])
            else:
                self.print_error("Docker container not found.")
        else:
            if script_file.exists():
                self.run_command(['conda', 'run', '-n', 'sage', 'python', str(script_file)])
            else:
                self.print_error(f"Example file not found: {script_path}")
    
    def show_help(self):
        """Show help and troubleshooting information."""
        self.print_header("SAGE Setup Help")
        
        print(f"{Colors.BOLD}📋 SETUP OPTIONS:{Colors.RESET}")
        print()
        print("1. Minimal Setup:")
        print("   • Quick Python-only installation")
        print("   • No Docker required")
        print("   • Pure Python implementation (slower performance)")
        print("   • Best for: Development, testing, quick start")
        print()
        print("2. Full Setup:")
        print("   • Complete installation with Docker")
        print("   • High-performance C++ extensions")
        print("   • All dependencies included (CANDY database)")
        print("   • Best for: Production, performance-critical applications")
        print()
        print(f"{Colors.BOLD}🔧 SYSTEM REQUIREMENTS:{Colors.RESET}")
        print()
        print("Minimal Setup:")
        print("   • Conda (Miniconda or Anaconda)")
        print("   • Python ≥ 3.11")
        print("   • Linux/macOS/Windows")
        print()
        print("Full Setup:")
        print("   • All minimal requirements")
        print("   • Docker and Docker Compose")
        print("   • 4GB+ RAM recommended")
        print("   • GPU support (optional but recommended)")
        print()
        print(f"{Colors.BOLD}🛠️ TROUBLESHOOTING:{Colors.RESET}")
        print()
        print("• Environment Issues:")
        print("  conda activate sage              # Activate SAGE environment")
        print("  conda env list                   # List all environments")
        print("  conda deactivate                 # Exit current environment")
        print()
        print("• After Minimal Setup:")
        print("  conda activate sage              # Must run after script exits")
        print("  python -c \"import sage\"          # Test installation")
        print("  ./activate_sage.sh               # Use convenience script")
        print()
        print("• After Full Setup:")
        print("  ./activate_sage.sh               # Use convenience script")
        print("  ssh root@localhost -p 2222      # Manual Docker connection")
        print("  conda activate sage              # Activate in Docker")
        print()
        print("• Hugging Face Authentication:")
        print("  export HF_ENDPOINT=https://hf-mirror.com")
        print("  huggingface-cli login --token <token>")
        print()
        print("• Performance Issues:")
        print("  Use Full Setup for C++ extensions")
        print()
        print("• Docker Issues:")
        print("  docker ps -a")
        print("  docker logs <container_name>")
        print()
        print(f"{Colors.BOLD}📚 DOCUMENTATION:{Colors.RESET}")
        print("   https://intellistream.github.io/SAGE-Pub/")
        print()
    
    def show_status(self):
        """Show current installation status."""
        self.print_header("SAGE Installation Status")
        
        setup_type = self.config.get('setup_type')
        installation_date = self.config.get('installation_date')
        
        if setup_type:
            print(f"{Colors.GREEN}✅ Setup Type: {setup_type.title()}{Colors.RESET}")
            if installation_date:
                import datetime
                date_str = datetime.datetime.fromtimestamp(installation_date).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{Colors.BLUE}📅 Installed: {date_str}{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ No SAGE installation found{Colors.RESET}")
        
        # Check conda environment
        if self.check_sage_env_exists():
            print(f"{Colors.GREEN}✅ Conda environment 'sage' exists{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ Conda environment 'sage' not found{Colors.RESET}")
        
        # Check Docker (for full setup)
        if setup_type == "full":
            container_name = self.config.get('docker_container')
            if container_name:
                print(f"{Colors.GREEN}✅ Docker container: {container_name}{Colors.RESET}")
                
                # Check if container is running
                running_container = self.get_docker_container_name()
                if running_container:
                    print(f"{Colors.GREEN}✅ Container is running{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}⚠️  Container is not running{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Docker container information not found{Colors.RESET}")
        
        # Show activation instructions
        print()
        if setup_type == "minimal":
            print(f"{Colors.BOLD}💡 To use SAGE:{Colors.RESET}")
            print(f"{Colors.GREEN}   conda activate sage{Colors.RESET}")
            print(f"{Colors.GREEN}   ./activate_sage.sh{Colors.RESET}")
        elif setup_type == "full":
            print(f"{Colors.BOLD}💡 To use SAGE:{Colors.RESET}")
            print(f"{Colors.GREEN}   ./activate_sage.sh{Colors.RESET}")
            print(f"{Colors.GREEN}   ssh root@localhost -p 2222{Colors.RESET}")
        
        print()
    
    def main_menu(self):
        """Show the main interactive menu."""
        while True:
            try:
                self.print_header("SAGE Project Installation")
                
                # Show status
                setup_type = self.config.get('setup_type')
                if setup_type:
                    if setup_type == "full":
                        print(f"{Colors.GREEN}🐳 Current setup: Full (Docker + SAGE environment){Colors.RESET}")
                        print(f"{Colors.BLUE}💡 To use: ./activate_sage.sh{Colors.RESET}")
                    elif setup_type == "minimal":
                        print(f"{Colors.GREEN}🔧 Current setup: Minimal (SAGE environment available){Colors.RESET}")
                        print(f"{Colors.BLUE}💡 To use: conda activate sage{Colors.RESET}")
                elif self.check_sage_env_exists():
                    print(f"{Colors.YELLOW}📦 Sage environment detected (type unknown){Colors.RESET}")
                    print(f"{Colors.BLUE}💡 To use: conda activate sage{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ No SAGE installation found{Colors.RESET}")
                
                print()
                print("Select an option:")
                print()
                print("1. Minimal Setup (Python-only, fast installation)")
                print("2. Full Setup (Docker + Conda, with C++ extensions)")
                print("3. Install Third-party Components (Kafka, etc.)")
                print("4. Run Example Scripts")
                print("5. Show Installation Status")
                print("6. Uninstall SAGE (Complete removal)")
                print("7. Help & Troubleshooting")
                print("8. Exit")
                print()
                print("=" * 60)
                
                choice = self.get_user_input("Enter your choice [1-8]: ", "8")
                
                if choice == "1":
                    self.minimal_setup()
                elif choice == "2":
                    self.full_setup()
                elif choice == "3":
                    self.install_third_party()
                elif choice == "4":
                    self.run_example_scripts()
                elif choice == "5":
                    self.show_status()
                elif choice == "6":
                    self.uninstall_sage()
                elif choice == "7":
                    self.show_help()
                elif choice == "8":
                    print(f"{Colors.GREEN}Exiting SAGE installer. Goodbye!{Colors.RESET}")
                    sys.exit(0)
                else:
                    self.print_error("Invalid choice. Please try again.")
                
                if not self.is_ci:
                    self.pause()
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Installation cancelled by user.{Colors.RESET}")
                sys.exit(0)
            except Exception as e:
                self.print_error(f"Unexpected error: {e}")
                if not self.is_ci:
                    self.pause()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SAGE Framework Installation Script")
    parser.add_argument('--minimal', action='store_true', help='Run minimal setup directly')
    parser.add_argument('--full', action='store_true', help='Run full setup directly')
    parser.add_argument('--uninstall', action='store_true', help='Uninstall SAGE completely')
    parser.add_argument('--status', action='store_true', help='Show installation status')
    parser.add_argument('--help-sage', action='store_true', help='Show SAGE help information')
    
    args = parser.parse_args()
    
    installer = SageInstaller()
    
    try:
        if args.minimal:
            installer.minimal_setup()
        elif args.full:
            installer.full_setup()
        elif args.uninstall:
            installer.uninstall_sage()
        elif args.status:
            installer.show_status()
        elif args.help_sage:
            installer.show_help()
        else:
            installer.main_menu()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Installation cancelled by user.{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        installer.print_error(f"Installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
