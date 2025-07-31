"""
System Management Module
=======================

Handles system-level dependencies and platform detection.
"""

import os
import platform
import subprocess
from pathlib import Path
from .base import BaseInstaller


class SystemManager(BaseInstaller):
    """Manages system dependencies and platform-specific operations."""
    
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
    
    def install_system_dependencies(self):
        """Install system dependencies for minimal setup."""
        self.print_step("Installing system dependencies...")
        
        deps_marker = self.sage_dir / "deps_installed"
        if deps_marker.exists():
            self.print_info("System dependencies already installed, skipping.")
            return
        
        # Detect package manager
        if platform.system() == "Linux":
            self._install_linux_dependencies()
        else:
            self.print_warning(f"Automatic dependency installation not supported on {platform.system()}")
            self.print_info("Please ensure you have build-essential, cmake, git, and swig installed")
            
        # Mark as installed
        deps_marker.touch()
        self.print_success("System dependencies installed")
    
    def _install_linux_dependencies(self):
        """Install dependencies on Linux systems."""
        try:
            # Try apt-get first (Debian/Ubuntu)
            self.run_command(['which', 'apt-get'], capture=True)
            self._install_apt_dependencies()
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Try yum (CentOS/RHEL)
                self.run_command(['which', 'yum'], capture=True)
                self._install_yum_dependencies()
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # Try dnf (Fedora)
                    self.run_command(['which', 'dnf'], capture=True)
                    self._install_dnf_dependencies()
                except (subprocess.CalledProcessError, FileNotFoundError):
                    self.print_warning("No supported package manager found")
                    self.print_info("Please install manually: build-essential cmake git swig")
    
    def _install_apt_dependencies(self):
        """Install dependencies using apt-get."""
        sudo_cmd = [] if self._is_root() else ['sudo']
        
        self.run_command(sudo_cmd + ['apt-get', 'update', '-y'])
        self.run_command(sudo_cmd + ['apt-get', 'install', '-y', '--no-install-recommends',
                                   'build-essential', 'cmake', 'git', 'swig', 'pkg-config', 'python3-dev'])
    
    def _install_yum_dependencies(self):
        """Install dependencies using yum."""
        sudo_cmd = [] if self._is_root() else ['sudo']
        
        self.run_command(sudo_cmd + ['yum', 'groupinstall', '-y', 'Development Tools'])
        self.run_command(sudo_cmd + ['yum', 'install', '-y', 'cmake', 'git', 'swig', 'pkgconfig', 'python3-devel'])
    
    def _install_dnf_dependencies(self):
        """Install dependencies using dnf."""
        sudo_cmd = [] if self._is_root() else ['sudo']
        
        self.run_command(sudo_cmd + ['dnf', 'groupinstall', '-y', 'Development Tools'])
        self.run_command(sudo_cmd + ['dnf', 'install', '-y', 'cmake', 'git', 'swig', 'pkgconf-devel', 'python3-devel'])
    
    def _is_root(self) -> bool:
        """Check if running as root."""
        return os.getuid() == 0 if hasattr(os, 'getuid') else False
    
    def is_running_in_docker(self) -> bool:
        """Check if we're running inside a Docker container."""
        try:
            # Check for .dockerenv file (most common indicator)
            if Path('/.dockerenv').exists():
                return True
            
            # Check for docker in cgroup
            with open('/proc/1/cgroup', 'r') as f:
                cgroup_content = f.read()
                if 'docker' in cgroup_content or 'containerd' in cgroup_content:
                    return True
                    
            # Check for container environment variables
            if any(env in os.environ for env in ['DOCKER_CONTAINER', 'CONTAINER', 'KUBERNETES_SERVICE_HOST']):
                return True
                
            return False
        except (FileNotFoundError, PermissionError, IOError):
            return False
    
    def install_cpp_build_dependencies(self):
        """Install additional C++ build dependencies for native compilation."""
        self.print_step("Installing C++ build dependencies...")
        
        cpp_deps_marker = self.sage_dir / "cpp_deps_installed"
        if cpp_deps_marker.exists():
            self.print_info("C++ build dependencies already installed, skipping.")
            return
        
        if platform.system() == "Linux":
            self._install_linux_cpp_dependencies()
        elif platform.system() == "Darwin":  # macOS
            self._install_macos_cpp_dependencies()
        else:
            self.print_warning(f"C++ dependency installation not supported on {platform.system()}")
            self.print_info("Please ensure you have: gcc/clang, cmake, pkg-config, BLAS/LAPACK libraries")
            return
            
        # Mark as installed
        cpp_deps_marker.touch()
        self.print_success("C++ build dependencies installed")
    
    def _install_linux_cpp_dependencies(self):
        """Install C++ build dependencies on Linux."""
        try:
            # Try apt-get first (Debian/Ubuntu)
            self.run_command(['which', 'apt-get'], capture=True)
            self._install_apt_cpp_dependencies()
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Try yum (CentOS/RHEL)
                self.run_command(['which', 'yum'], capture=True)
                self._install_yum_cpp_dependencies()
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # Try dnf (Fedora)
                    self.run_command(['which', 'dnf'], capture=True)
                    self._install_dnf_cpp_dependencies()
                except (subprocess.CalledProcessError, FileNotFoundError):
                    self.print_warning("No supported package manager found")
                    self.print_info("Please install manually: gcc g++ libblas-dev liblapack-dev libfaiss-dev")
    
    def _install_apt_cpp_dependencies(self):
        """Install C++ dependencies using apt-get."""
        sudo_cmd = [] if self._is_root() else ['sudo']
        
        self.print_info("Installing BLAS, LAPACK, and FAISS dependencies...")
        self.run_command(sudo_cmd + ['apt-get', 'update', '-y'])
        self.run_command(sudo_cmd + ['apt-get', 'install', '-y', '--no-install-recommends',
                                   'gcc', 'g++', 'libblas-dev', 'liblapack-dev', 'libopenblas-dev',
                                   'libfaiss-dev', 'pybind11-dev', 'libeigen3-dev'])
    
    def _install_yum_cpp_dependencies(self):
        """Install C++ dependencies using yum."""
        sudo_cmd = [] if self._is_root() else ['sudo']
        
        self.print_info("Installing BLAS, LAPACK, and development libraries...")
        self.run_command(sudo_cmd + ['yum', 'install', '-y', 'gcc', 'gcc-c++', 'blas-devel', 
                                   'lapack-devel', 'openblas-devel', 'eigen3-devel'])
    
    def _install_dnf_cpp_dependencies(self):
        """Install C++ dependencies using dnf."""
        sudo_cmd = [] if self._is_root() else ['sudo']
        
        self.print_info("Installing BLAS, LAPACK, and development libraries...")
        self.run_command(sudo_cmd + ['dnf', 'install', '-y', 'gcc', 'gcc-c++', 'blas-devel',
                                   'lapack-devel', 'openblas-devel', 'eigen3-devel'])
    
    def _install_macos_cpp_dependencies(self):
        """Install C++ dependencies on macOS."""
        try:
            # Check if Homebrew is available
            self.run_command(['which', 'brew'], capture=True)
            self.print_info("Installing dependencies via Homebrew...")
            self.run_command(['brew', 'install', 'cmake', 'openblas', 'lapack', 'eigen', 'faiss'])
            self.print_success("macOS C++ dependencies installed via Homebrew")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_warning("Homebrew not found. Please install Homebrew first:")
            self.print_info("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            self.print_info("Or manually install: cmake, openblas, lapack, eigen, faiss")
