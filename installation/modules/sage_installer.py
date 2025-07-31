"""
SAGE Installation Orchestrator
=============================

Main installer class that orchestrates all installation modules.
"""

import os
import sys
import time
from pathlib import Path
from .base import BaseInstaller
from .system_manager import SystemManager
from .conda_manager import CondaManager
from .docker_manager import DockerManager
from .package_manager import PackageManager
from .menu_handler import MenuHandler


class SageInstaller(BaseInstaller):
    """Main SAGE installation orchestrator that coordinates all modules."""
    
    def __init__(self, conda_env_name: str = "sage"):
        super().__init__(conda_env_name)
        
        # Initialize all modules
        self.system_manager = SystemManager(conda_env_name)
        self.conda_manager = CondaManager(conda_env_name)
        self.docker_manager = DockerManager(conda_env_name)
        self.package_manager = PackageManager(conda_env_name)
        self.menu_handler = MenuHandler(conda_env_name)
        
        # Sync configuration across modules
        for module in [self.system_manager, self.conda_manager, self.docker_manager, 
                      self.package_manager, self.menu_handler]:
            module.config = self.config
            module.conda_env_name = self.conda_env_name
    
    def minimal_setup(self):
        """Perform minimal Python-only installation."""
        self.print_header("SAGE Minimal Setup")
        print(f"⚠️  Python-only installation (no C++ extensions)")
        print(f"   - Faster installation and setup")
        print(f"   - Pure Python implementation")
        print(f"   - Suitable for development and testing\n")
        
        try:
            self.system_manager.install_system_dependencies()
            self.conda_manager.create_conda_environment()
            self.conda_manager.install_python_packages(minimal=True)
            
            # Optional HF authentication
            if not self.is_ci:
                configure_hf = self.confirm_action("Configure Hugging Face authentication now?")
                if configure_hf:
                    self.conda_manager.setup_huggingface_auth()
            
            # Save configuration
            self.config['setup_type'] = 'minimal'
            self.config['conda_env_name'] = self.conda_env_name
            self.config['installation_date'] = time.time()
            self.save_config()
            
            # Success message with activation instructions
            self.print_header("Installation Complete!")
            self.print_success("Minimal setup completed successfully!")
            print()
            print(f"📝 Note: This version uses pure Python (no C++ extensions)")
            print(f"🚀 Automatically activating SAGE environment...")
            print()
            
            # Create activation script for future use
            self.package_manager.create_activation_script('minimal')
            
            # Auto-activate the environment if not in CI
            if not self.is_ci:
                self.print_success("🚀 Automatically activating SAGE environment...")
                print(f"✅ You will now be dropped into the SAGE conda environment")
                print(f"📝 Your prompt will show (sage) when active")
                print(f"💡 To exit the environment later, type: conda deactivate")
                print(f"💡 To reactivate later, use: ./activate_sage.sh")
                print()
                
                # Test import before activation
                test_passed = self._test_sage_import()
                
                if test_passed:
                    print(f"✅ SAGE installation verified!")
                    self._auto_activate_conda()
                else:
                    print(f"⚠️  Installation completed but import test failed")
                    print(f"💡 Try activating manually: conda activate {self.conda_env_name}")
            else:
                self.print_info(f"CI mode: Environment ready for activation with 'conda activate {self.conda_env_name}'")
            
        except Exception as e:
            self.print_error(f"Minimal setup failed: {e}")
            raise
    
    def native_cpp_setup(self):
        """Perform installation with native C++ extensions (without Docker)."""
        self.print_header("SAGE Native C++ Setup")
        print(f"🔧 Installation with native C++ extensions:")
        print(f"   - Native compilation on host system")
        print(f"   - High-performance C++ extensions")
        print(f"   - No Docker container required")
        print(f"   - ⚠️  May require manual dependency management\n")
        
        from .base import Colors
        
        # Check if we're in Docker - if not, show additional warnings
        if not self.system_manager.is_running_in_docker():
            print(f"{Colors.YELLOW}🚨 IMPORTANT CONSIDERATIONS:{Colors.RESET}")
            print(f"   • This method compiles C++ extensions directly on your system")
            print(f"   • Docker-based setup is more reliable and recommended")
            print(f"   • Native build may have platform-specific issues")
            print(f"   • Requires system development tools and libraries")
            print()
            print(f"{Colors.BOLD}Better alternative: Full Setup with Docker{Colors.RESET}")
            print(f"   Run: python install.py --full")
            print()
            
            if not self.confirm_action("Continue with native C++ build?"):
                self.print_info("Setup cancelled. Consider Docker-based installation for best experience.")
                return
        
        try:
            # Install system dependencies (including C++ build tools)
            self.system_manager.install_system_dependencies()
            self.system_manager.install_cpp_build_dependencies()
            
            # Create conda environment
            self.conda_manager.create_conda_environment()
            
            # Install SAGE with C++ extension support
            self.package_manager.install_python_packages_with_cpp(native_build=True)
            
            # Optional HF authentication
            if not self.is_ci:
                configure_hf = self.confirm_action("Configure Hugging Face authentication now?")
                if configure_hf:
                    self.conda_manager.setup_huggingface_auth()
            
            # Save configuration
            self.config['setup_type'] = 'native_cpp'
            self.config['conda_env_name'] = self.conda_env_name
            self.config['installation_date'] = time.time()
            self.save_config()
            
            # Success message with activation instructions
            self.print_header("Installation Complete!")
            self.print_success("Native C++ setup completed successfully!")
            print()
            print(f"🔧 Native C++ extensions have been built and installed")
            print(f"🚀 High-performance SAGE ready for use")
            print()
            
            # Create activation script for future use
            self.package_manager.create_activation_script('minimal')  # Use minimal script since no Docker
            
            # Auto-activate the environment if not in CI
            if not self.is_ci:
                self.print_success("🚀 Automatically activating SAGE environment...")
                print(f"✅ You will now be dropped into the SAGE conda environment")
                print(f"📝 Your prompt will show ({self.conda_env_name}) when active")
                print(f"💡 To exit the environment later, type: conda deactivate")
                print(f"💡 To reactivate later, use: ./activate_sage.sh")
                print()
                
                # Test import and C++ extensions
                test_passed = self._test_sage_import_with_cpp()
                
                if test_passed:
                    print(f"✅ SAGE with C++ extensions verified!")
                    self._auto_activate_conda()
                else:
                    print(f"⚠️  Installation completed but C++ extension test failed")
                    print(f"💡 Try activating manually: conda activate {self.conda_env_name}")
            else:
                self.print_info(f"CI mode: Environment ready for activation with 'conda activate {self.conda_env_name}'")
            
        except Exception as e:
            self.print_error(f"Native C++ setup failed: {e}")
            self.print_info("Consider using Docker-based Full Setup for more reliable installation")
            raise
    
    def full_setup(self):
        """Perform full installation with Docker and C++ extensions."""
        self.print_header("SAGE Full Setup")
        print(f"✅ Complete installation with Docker and C++ extensions:")
        print(f"   - Docker container environment")
        print(f"   - High-performance C++ extensions") 
        print(f"   - CANDY vector database")
        print(f"   - Production-ready configuration\n")
        
        # Check Docker
        if not self.docker_manager.check_docker_installed():
            self.print_error("Docker is not installed. Please install Docker and try again.")
            self.print_info("Download from: https://docs.docker.com/get-docker/")
            raise RuntimeError("Docker not found")
        
        try:
            # 1. Pull Docker image if needed
            self.docker_manager.pull_docker_image()
            
            # 2. Start Docker container
            self.docker_manager.start_docker_container()
            
            # 3. Get container name
            container_name = self.docker_manager.get_docker_container_name()
            if not container_name:
                self.print_error("Failed to detect running Docker container")
                raise RuntimeError("No Docker container found")
            self.print_success(f"Docker container '{container_name}' is running")
            
            # 4. Install system dependencies in Docker
            self.docker_manager.install_docker_dependencies(container_name)
            
            # 5. Create conda environment in Docker
            self.docker_manager.setup_docker_conda_environment(container_name)
            
            # 6. Install SAGE with C++ extensions
            self.package_manager.install_sage_packages_in_docker(container_name, with_cpp=True)
            
            # Optional HF authentication
            if not self.is_ci:
                configure_hf = self.confirm_action("Configure Hugging Face authentication now?")
                if configure_hf:
                    self._setup_docker_huggingface_auth(container_name)
            
            # 8. Save configuration
            self.config['setup_type'] = 'full'
            self.config['conda_env_name'] = self.conda_env_name
            self.config['docker_container'] = container_name
            self.config['installation_date'] = time.time()
            self.save_config()
            
            # 9. Success message and activation instructions
            self.print_header("Installation Complete!")
            self.print_success("Full setup completed successfully!")
            print()
            print(f"🐳 TO ACCESS THE DOCKER ENVIRONMENT:")
            print(f"   ssh root@localhost -p 2222")
            print(f"   OR: docker exec -it {container_name} bash")
            print()
            print(f"🔧 ONCE IN DOCKER, ACTIVATE SAGE ENVIRONMENT:")
            print(f"   conda activate {self.conda_env_name}")
            print()
            print(f"📝 You'll then see ({self.conda_env_name}) in your prompt")
            print(f"🚀 C++ extensions and all features available")
            print()
            print(f"🚀 Quick test after activation:")
            print(f"   python -c \"import sage; print('SAGE with C++ extensions ready!')\"")
            print()
            
            # Create activation script
            self.package_manager.create_activation_script('full', container_name)
            
            # Test SAGE installation in Docker container
            if not self.is_ci:
                test_sage = self.confirm_action("Test SAGE installation in Docker now?")
                if test_sage:
                    self._test_sage_in_docker(container_name)
                
                # Ask if user wants to activate now
                activate_now = self.confirm_action("Activate SAGE environment in Docker now?")
                if activate_now:
                    self._activate_docker_environment()
                else:
                    print(f"💡 To activate SAGE later, run: ./activate_sage.sh")
            else:
                self.print_info("CI mode: Use './activate_sage.sh' or 'docker exec -it container bash' to access the environment")
            
        except Exception as e:
            self.print_error(f"Full setup failed: {e}")
            raise
    
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
            self.conda_manager.remove_conda_environment()
            
            # Remove Docker containers and images
            self.docker_manager.remove_docker_containers()
            
            # Clean up build artifacts
            self.package_manager.clean_build_artifacts()
            
            # Remove setup directory
            if self.sage_dir.exists():
                import shutil
                shutil.rmtree(self.sage_dir)
                self.print_success("Setup markers removed")
            
            # Remove activation script
            activation_script = self.project_root / "activate_sage.sh"
            if activation_script.exists():
                activation_script.unlink()
                self.print_success("Removed activation script")
            
            # Optional: Clean up Hugging Face cache
            self.menu_handler.clean_huggingface_cache()
            
            self.print_header("Uninstallation Complete!")
            self.print_success("SAGE completely uninstalled!")
            self.print_success("Environment reset to clean state")
            
        except Exception as e:
            self.print_error(f"Uninstallation failed: {e}")
            raise
    
    def main_menu(self):
        """Show the main interactive menu."""
        while True:
            try:
                choice = self.menu_handler.show_main_menu()
                
                if choice == "1":
                    self.minimal_setup()
                elif choice == "2":
                    self.full_setup()
                elif choice == "3":
                    self.native_cpp_setup()
                elif choice == "4":
                    self.package_manager.install_third_party_components()
                elif choice == "5":
                    self.menu_handler.run_example_scripts()
                elif choice == "6":
                    self.menu_handler.show_status()
                elif choice == "7":
                    self.uninstall_sage()
                elif choice == "8":
                    self.menu_handler.show_help()
                elif choice == "9":
                    print(f"Exiting SAGE installer. Goodbye!")
                    sys.exit(0)
                else:
                    self.print_error("Invalid choice. Please try again.")
                
                if not self.is_ci:
                    self.pause()
                    
            except KeyboardInterrupt:
                print(f"\nInstallation cancelled by user.")
                sys.exit(0)
            except Exception as e:
                self.print_error(f"Unexpected error: {e}")
                if not self.is_ci:
                    self.pause()
    
    def _test_sage_import(self) -> bool:
        """Test SAGE import in minimal setup."""
        try:
            result = self.run_command([
                'conda', 'run', '-n', self.conda_env_name, 'python', '-c', 
                'import sage; print("SAGE ready!")'
            ], capture=True, check=False)
            
            if result.returncode == 0:
                self.print_success("SAGE import test passed! 🎉")
                return True
            else:
                self.print_warning("SAGE import test failed")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                return False
        except Exception as e:
            self.print_warning(f"Failed to test SAGE import: {e}")
            return False
    
    def _test_sage_in_docker(self, container_name: str):
        """Test SAGE installation in Docker container."""
        self.print_step("Testing SAGE installation...")
        try:
            test_result = self.run_command([
                'docker', 'exec', '-i', container_name, 'bash', '-c',
                f'''
                source /opt/conda/bin/activate &&
                conda activate {self.conda_env_name} &&
                python -c "import sage; print('SAGE with C++ extensions ready!')"
                '''
            ], capture=True, check=False)
            
            if test_result.returncode == 0:
                self.print_success("SAGE test passed! 🎉")
                print(f"   {test_result.stdout.strip()}")
            else:
                self.print_warning("SAGE test failed")
                if test_result.stderr:
                    print(f"   Error: {test_result.stderr.strip()}")
        except Exception as e:
            self.print_warning(f"Failed to test SAGE: {e}")
    
    def _auto_activate_conda(self):
        """Auto-activate conda environment for minimal setup."""
        try:
            # Execute the activation script
            activation_script = self.project_root / "activate_sage.sh"
            if activation_script.exists():
                self.run_command(['bash', str(activation_script)], check=False)
            else:
                self.print_info(f"To activate SAGE manually: conda activate {self.conda_env_name}")
        except Exception as e:
            self.print_warning(f"Failed to auto-activate: {e}")
            self.print_info(f"To activate SAGE manually: conda activate {self.conda_env_name}")
    
    def _activate_docker_environment(self):
        """Activate SAGE environment in Docker."""
        self.print_success("🚀 Launching SAGE environment in Docker...")
        print(f"📝 You'll be dropped into the Docker container with SAGE activated")
        print(f"💡 Type 'exit' to return to your host system")
        print()
        
        # Use the activation script
        activation_script = self.project_root / "activate_sage.sh"
        if activation_script.exists():
            try:
                # Execute the activation script
                self.run_command(['bash', str(activation_script)], check=False)
            except KeyboardInterrupt:
                print(f"\nExited Docker environment")
            except Exception as e:
                self.print_warning(f"Failed to activate: {e}")
                self.print_info("You can manually activate with: ./activate_sage.sh")
        else:
            self.print_error("Activation script not found")
    
    def _setup_docker_huggingface_auth(self, container_name: str):
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
                f'''
                source /opt/conda/bin/activate &&
                conda activate {self.conda_env_name} &&
                HF_ENDPOINT={hf_endpoint} huggingface-cli login --token "{hf_token}"
                '''
            ])
            self.print_success("Hugging Face authentication configured in Docker")
        except Exception:
            self.print_error("Failed to configure Hugging Face authentication in Docker")
    
    def _test_sage_import_with_cpp(self) -> bool:
        """Test SAGE import with C++ extensions."""
        try:
            result = self.run_command([
                'conda', 'run', '-n', self.conda_env_name, 'python', '-c', 
                '''
import sage
print("SAGE imported successfully!")
try:
    # Try to import C++ extensions if available
    from sage_ext import get_extension_manager
    manager = get_extension_manager()
    print(f"C++ extensions available: {list(manager.available_extensions.keys()) if hasattr(manager, 'available_extensions') else 'Unknown'}")
    print("SAGE with C++ extensions ready!")
except ImportError:
    print("SAGE ready (C++ extensions not available)")
                '''
            ], capture=True, check=False)
            
            if result.returncode == 0:
                self.print_success("SAGE with C++ extensions test passed! 🎉")
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines:
                    if line.strip():
                        print(f"   {line}")
                return True
            else:
                self.print_warning("SAGE C++ extension test failed")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                return False
        except Exception as e:
            self.print_warning(f"Failed to test SAGE with C++ extensions: {e}")
            return False
