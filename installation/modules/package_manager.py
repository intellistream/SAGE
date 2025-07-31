"""
Package Management Module
=========================

Handles SAGE package installation and C++ extensions.
"""

import os
import subprocess
import shutil
from pathlib import Path
from .base import BaseInstaller


class PackageManager(BaseInstaller):
    """Manages SAGE package installation and C++ extensions."""
    
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
                # Make executable and run
                build_script.chmod(0o755)
                self.run_command(['bash', str(build_script)], cwd=extension_dir)
                self.print_success(f"Extension '{extension_name}' built successfully")
                built_any = True
            except Exception as e:
                self.print_error(f"Failed to build extension '{extension_name}': {e}")
                failed_builds.append(extension_name)
        
        if built_any:
            self.print_success("Extension libraries built successfully")
        
        if failed_builds:
            self.print_warning(f"Failed to build extensions: {', '.join(failed_builds)}")
            return False
            
        return built_any
    
    def build_sage_ext_libraries_native(self):
        """Build C++ extensions natively (without Docker) with warnings."""
        from .base import Colors
        
        # Check if we're in a Docker container
        from .system_manager import SystemManager
        sys_manager = SystemManager()
        
        if not sys_manager.is_running_in_docker():
            self.print_header("⚠️  Native C++ Extension Build Warning")
            print(f"{Colors.YELLOW}You are about to build C++ extensions directly on your host system.{Colors.RESET}")
            print()
            print(f"{Colors.BOLD}RECOMMENDED: Use Docker-based installation instead{Colors.RESET}")
            print(f"  • More reliable and consistent build environment")
            print(f"  • Pre-configured dependencies and tools")
            print(f"  • Isolated from host system")
            print()
            print(f"{Colors.BOLD}Native build considerations:{Colors.RESET}")
            print(f"  • Requires system C++ development tools")
            print(f"  • May conflict with existing libraries")
            print(f"  • Platform-specific issues possible")
            print(f"  • Manual dependency management required")
            print()
            
            if not self.confirm_action("Continue with native C++ build anyway?"):
                self.print_info("Cancelled. Consider using Full Setup with Docker for best experience.")
                return False
        else:
            self.print_info("Detected Docker environment - proceeding with native build...")
        
        # Install C++ build dependencies
        sys_manager.install_cpp_build_dependencies()
        
        # Build extensions using the existing logic
        return self.build_sage_ext_libraries()
    
    def install_python_packages_with_cpp(self, native_build: bool = False):
        """Install Python packages with C++ extensions support."""
        self.print_step("Installing Python packages with C++ extension support...")
        
        try:
            # Set environment variables for C++ build
            env = os.environ.copy()
            env['SAGE_INSTALLER_ACTIVE'] = 'true'
            env['SAGE_MINIMAL_INSTALL'] = 'false'
            env['SAGE_QUEUE_BACKEND'] = 'sage'
            
            if native_build:
                env['SAGE_NATIVE_BUILD'] = 'true'
                self.print_info("Building with native C++ compilation")
            
            # Install conda dependencies for C++ builds
            self.print_step("Installing conda build dependencies...")
            self.run_command(['conda', 'run', '-n', self.conda_env_name, 'conda', 'install', '-c', 'conda-forge',
                            'pkg-config', 'cmake', 'pybind11', 'numpy', '-y'])
            
            # Install the main SAGE package with C++ support
            self.run_command_with_progress(
                ['conda', 'run', '-n', self.conda_env_name, 'pip', 'install', '.'], 
                "Installing SAGE with C++ extension support",
                env=env
            )
            
            self.print_success("Python packages with C++ support installed successfully.")
            
            # Build C++ extensions
            if native_build:
                extensions_built = self.build_sage_ext_libraries_native()
            else:
                extensions_built = self.build_sage_ext_libraries()
            
            if extensions_built:
                self.print_success("C++ extensions built successfully!")
                self.print_info("Using high-performance SAGE with C++ extensions")
            else:
                self.print_warning("C++ extensions failed to build, falling back to Ray Queue")
                # Reinstall with Ray backend as fallback
                env['SAGE_MINIMAL_INSTALL'] = 'true'
                env['SAGE_QUEUE_BACKEND'] = 'ray'
                self.run_command(['conda', 'run', '-n', self.conda_env_name, 'pip', 'install', '.', '--force-reinstall'],
                               env=env)
                
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install Python packages with C++ support: {e}")
            raise
    
    def install_sage_packages_in_docker(self, container_name: str, with_cpp: bool = False):
        """Install SAGE packages in Docker container."""
        if with_cpp:
            self.print_step("Installing SAGE with C++ extensions in Docker...")
        else:
            self.print_step("Installing SAGE (minimal) in Docker...")
        
        try:
            # Set environment variables
            env_vars = "SAGE_INSTALLER_ACTIVE=true"
            if with_cpp:
                env_vars += " SAGE_MINIMAL_INSTALL=false SAGE_QUEUE_BACKEND=sage"
            else:
                env_vars += " SAGE_MINIMAL_INSTALL=true SAGE_QUEUE_BACKEND=ray"
            
            # Install SAGE package
            self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                f'''
                source /opt/conda/bin/activate &&
                conda activate {self.conda_env_name} &&
                cd /workspace &&
                {env_vars} pip install .
                '''
            ])
            
            if with_cpp:
                self.print_success("SAGE with C++ extensions installed in Docker")
                
                # Build C++ extensions if requested
                extensions_built = self.build_sage_ext_in_docker(container_name)
                
                if extensions_built:
                    self.print_info("Using high-performance SAGE with C++ extensions")
                    self.print_info("Available extensions may include: SageQueue, SAGE.DB, and other optimized components")
                else:
                    self.print_warning("C++ extensions failed, falling back to Ray Queue")
                    # Reinstall with Ray backend as fallback
                    self.run_command([
                        'docker', 'exec', '-i', container_name, 'bash', '-c',
                        f'''
                        source /opt/conda/bin/activate &&
                        conda activate {self.conda_env_name} &&
                        cd /workspace &&
                        SAGE_MINIMAL_INSTALL=true SAGE_INSTALLER_ACTIVE=true SAGE_QUEUE_BACKEND=ray pip install . --force-reinstall
                        '''
                    ])
            else:
                self.print_success("SAGE (minimal) installed in Docker")
                self.print_info("Using Ray Queue for communication")
            
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install SAGE in container: {e}")
            raise
    
    def build_sage_ext_in_docker(self, container_name: str) -> bool:
        """Build C++ extensions in Docker container."""
        self.print_step("Building SAGE C++ extensions in Docker...")
        self.print_info("Scanning sage_ext directory for all available extensions...")
        
        try:
            # First, list all available extensions
            list_result = self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                '''
                cd /workspace &&
                find sage_ext -name "build.sh" -type f | while read build_script; do
                    echo "Found extension: $(dirname "$build_script")"
                done
                '''
            ], capture=True, check=False)
            
            if list_result.stdout.strip():
                self.print_info("Available extensions:")
                for line in list_result.stdout.strip().split('\n'):
                    if line.strip():
                        self.print_info(f"  • {line.strip()}")
            else:
                self.print_warning("No C++ extensions found in sage_ext directory")
                return False
            
            # Build all extensions
            result = self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                f'''
                source /opt/conda/bin/activate &&
                conda activate {self.conda_env_name} &&
                cd /workspace &&
                
                build_count=0
                success_count=0
                
                find sage_ext -name "build.sh" -type f | while read build_script; do
                    extension_name=$(basename "$(dirname "$build_script")")
                    echo "Building extension: $extension_name"
                    chmod +x "$build_script"
                    
                    cd "$(dirname "$build_script")"
                    if bash "./$(basename "$build_script")"; then
                        echo "✅ $extension_name: BUILD SUCCESS"
                        success_count=$((success_count + 1))
                    else
                        echo "❌ $extension_name: BUILD FAILED"
                    fi
                    cd /workspace
                    build_count=$((build_count + 1))
                done
                
                echo "SUMMARY: Built $build_count extensions"
                '''
            ], capture=True, check=False)
            
            if result.returncode == 0:
                self.print_success("SAGE C++ extensions built successfully")
                if result.stdout:
                    # Show build summary
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if '✅' in line or '❌' in line or 'SUMMARY:' in line:
                            print(f"   {line}")
                
                return True
            else:
                self.print_warning("Some C++ extensions failed to build")
                if result.stderr:
                    self.print_warning(f"Build errors: {result.stderr.strip()}")
                # Still return True if at least some built
                if '✅' in result.stdout:
                    self.print_info("Some extensions built successfully, continuing...")
                    return True
                return False
                
        except Exception as e:
            self.print_warning(f"C++ extensions build failed: {e}")
            return False
    
    def install_third_party_components(self):
        """Install third-party components like Kafka."""
        self.print_header("Third-party Components")
        print("Available optional components:")
        print(f"ℹ️  Note: Core dependencies (CANDY, Docker) are installed in Full Setup")
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
    
    def clean_build_artifacts(self):
        """Clean up build artifacts and cache files."""
        self.print_step("Cleaning up build artifacts...")
        
        # Remove build directories
        for build_dir in ['build', 'sage.egg-info']:
            build_path = self.project_root / build_dir
            if build_path.exists():
                shutil.rmtree(build_path)
                self.print_success(f"Removed {build_dir} directory")
        
        # Remove compiled C extensions from sage_ext directory
        sage_ext_dir = self.project_root / "sage_ext"
        if sage_ext_dir.exists():
            for so_file in sage_ext_dir.rglob("*.so"):
                so_file.unlink()
            for build_dir in sage_ext_dir.rglob("build"):
                if build_dir.is_dir():
                    shutil.rmtree(build_dir)
            self.print_success("Removed compiled C extensions")
        
        # Remove Python cache
        for cache_dir in self.project_root.rglob("__pycache__"):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)
        
        for pyc_file in self.project_root.rglob("*.pyc"):
            pyc_file.unlink()
        
        self.print_success("Cleaned Python cache files")
    
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

# Activate the conda environment
conda activate {self.conda_env_name}

if [ $? -eq 0 ]; then
    echo "✅ SAGE environment activated successfully!"
    echo "📝 You are now in the ({self.conda_env_name}) environment"
    echo "🚀 Test with: python -c 'import sage; print(\"SAGE ready!\")'"
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
        echo ""
        echo "📋 You will be dropped into Docker with ({self.conda_env_name}) conda environment active"
        echo "💡 Type 'exit' to return to your host system"
        echo ""
        
        # Execute docker with proper conda activation and persistent environment
        docker exec -it "$CONTAINER_NAME" bash -c '
            source /opt/conda/etc/profile.d/conda.sh
            conda activate {self.conda_env_name}
            echo "✅ SAGE environment activated successfully!"
            echo "📝 You are now in the ({self.conda_env_name}) environment inside Docker"
            echo "🚀 Test with: python -c \\"import sage\\""
            echo ""
            export PS1="({self.conda_env_name}) \\u@\\h:\\w# "
            exec bash --norc --noprofile
        '
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
