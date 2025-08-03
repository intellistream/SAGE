"""
Menu and User Interface Handler
==============================

Handles interactive menus, status display, and user interactions.
"""

import datetime
import shutil
import time
from pathlib import Path
from .base import BaseInstaller, Colors


class MenuHandler(BaseInstaller):
    """Handles user interface, menus, and status display."""
    
    def show_main_menu(self):
        """Show the main interactive menu."""
        # Ask for environment name if not already set and not in CI mode
        if not self.is_ci and self.conda_env_name == "sage":
            print(f"{Colors.BOLD}🔧 Conda Environment Configuration{Colors.RESET}")
            print()
            print("You can choose a custom name for your conda environment.")
            print(f"Current default: {Colors.GREEN}sage{Colors.RESET}")
            print()
            
            custom_env = self.get_user_input("Enter custom environment name (press Enter for 'sage'): ", "sage").strip()
            if custom_env and custom_env != "sage":
                self.conda_env_name = custom_env
                # Sync the environment name change across all modules
                if hasattr(self, '_parent_installer'):
                    self._parent_installer.conda_env_name = custom_env
                    self._parent_installer.sync_conda_env_name()
                self.print_info(f"Environment name set to: {Colors.GREEN}{self.conda_env_name}{Colors.RESET}")
            else:
                self.print_info(f"Using default environment name: {Colors.GREEN}sage{Colors.RESET}")
            print()
        
        while True:
            try:
                self.print_header("SAGE Project Installation")
                
                # Show current environment name
                print(f"{Colors.BOLD}📦 Conda Environment: {Colors.GREEN}{self.conda_env_name}{Colors.RESET}")
                print()
                
                # Show status
                setup_type = self.config.get('setup_type')
                if setup_type:
                    if setup_type == "full":
                        print(f"{Colors.GREEN}🐳 Current setup: Full (Docker + SAGE environment){Colors.RESET}")
                        print(f"{Colors.BLUE}💡 To use: ./activate_sage.sh{Colors.RESET}")
                    elif setup_type == "minimal":
                        print(f"{Colors.GREEN}🔧 Current setup: Minimal (SAGE environment available){Colors.RESET}")
                        print(f"{Colors.BLUE}💡 To use: conda activate {self.conda_env_name}{Colors.RESET}")
                    elif setup_type == "native_cpp":
                        print(f"{Colors.GREEN}⚡ Current setup: Native C++ (SAGE with C++ extensions){Colors.RESET}")
                        print(f"{Colors.BLUE}💡 To use: conda activate {self.conda_env_name}{Colors.RESET}")
                elif self._check_sage_env_exists():
                    print(f"{Colors.YELLOW}📦 Sage environment detected (type unknown){Colors.RESET}")
                    print(f"{Colors.BLUE}💡 To use: conda activate {self.conda_env_name}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ No SAGE installation found{Colors.RESET}")
                
                print()
                print("Select an option:")
                print()
                print("1. Minimal Setup (Python-only, fast installation)")
                print("2. Full Setup (Docker + Conda, with C++ extensions) [RECOMMENDED]")
                print("3. Native C++ Setup (C++ extensions without Docker) ⚠️  [ADVANCED]")
                print("4. Install Third-party Components (Kafka, etc.)")
                print("5. Run Example Scripts")
                print("6. Show Installation Status")
                print("7. Uninstall SAGE (Complete removal)")
                print("8. Help & Troubleshooting")
                print("9. Exit")
                print()
                print("=" * 60)
                
                choice = self.get_user_input("Enter your choice [1-9]: ", "9")
                
                return choice
                    
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Installation cancelled by user.{Colors.RESET}")
                return "8"
            except Exception as e:
                self.print_error(f"Unexpected error: {e}")
                if not self.is_ci:
                    self.pause()
                return "8"
    
    def show_status(self):
        """Show current installation status."""
        self.print_header("SAGE Installation Status")
        
        setup_type = self.config.get('setup_type')
        installation_date = self.config.get('installation_date')
        
        if setup_type:
            print(f"{Colors.GREEN}✅ Setup Type: {setup_type.title()}{Colors.RESET}")
            if installation_date:
                date_str = datetime.datetime.fromtimestamp(installation_date).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{Colors.BLUE}📅 Installed: {date_str}{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ No SAGE installation found{Colors.RESET}")
        
        # Check conda environment
        if self._check_sage_env_exists():
            print(f"{Colors.GREEN}✅ Conda environment '{self.conda_env_name}' exists{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ Conda environment '{self.conda_env_name}' not found{Colors.RESET}")
        
        # Check Docker (for full setup)
        if setup_type == "full":
            container_name = self.config.get('docker_container')
            if container_name:
                print(f"{Colors.GREEN}✅ Docker container: {container_name}{Colors.RESET}")
                
                # Check if container is running
                running_container = self._get_docker_container_name()
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
            print(f"{Colors.GREEN}   conda activate {self.conda_env_name}{Colors.RESET}")
            print(f"{Colors.GREEN}   ./activate_sage.sh{Colors.RESET}")
        elif setup_type == "native_cpp":
            print(f"{Colors.BOLD}💡 To use SAGE:{Colors.RESET}")
            print(f"{Colors.GREEN}   conda activate {self.conda_env_name}{Colors.RESET}")
            print(f"{Colors.GREEN}   ./activate_sage.sh{Colors.RESET}")
            print(f"{Colors.BLUE}   (C++ extensions compiled natively){Colors.RESET}")
        elif setup_type == "full":
            print(f"{Colors.BOLD}💡 To use SAGE:{Colors.RESET}")
            print(f"{Colors.GREEN}   ./activate_sage.sh{Colors.RESET}")
            print(f"{Colors.GREEN}   ssh root@localhost -p 2222{Colors.RESET}")
        
        print()
    
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
        print("3. Native C++ Setup:")
        print("   • C++ extensions compiled directly on host system")
        print("   • No Docker container required")
        print("   • ⚠️  Requires manual dependency management")
        print("   • Best for: Users already in Docker containers or with specific build requirements")
        print("   • Recommended: Use Full Setup with Docker for most users")
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
        print(f"  conda activate {self.conda_env_name}              # Activate SAGE environment")
        print("  conda env list                   # List all environments")
        print("  conda deactivate                 # Exit current environment")
        print()
        print("• After Minimal Setup:")
        print(f"  conda activate {self.conda_env_name}              # Must run after script exits")
        print("  python -c \"import sage\"          # Test installation")
        print("  ./activate_sage.sh               # Use convenience script")
        print()
        print("• After Full Setup:")
        print("  ./activate_sage.sh               # Use convenience script")
        print("  ssh root@localhost -p 2222      # Manual Docker connection")
        print(f"  conda activate {self.conda_env_name}              # Activate in Docker")
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
    
    def clean_huggingface_cache(self):
        """Clean up Hugging Face cache and tokens."""
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
    
    def _check_sage_env_exists(self) -> bool:
        """Check if sage conda environment exists."""
        try:
            result = self.run_command(['conda', 'env', 'list'], capture=True)
            env_lines = result.stdout.strip().split('\n')
            for line in env_lines:
                if line.strip().startswith(self.conda_env_name + ' ') or line.strip().startswith(self.conda_env_name + '\t'):
                    return True
            return False
        except Exception:
            return False
    
    def _get_docker_container_name(self):
        """Get the name of the running SAGE Docker container."""
        try:
            result = self.run_command([
                'docker', 'ps', '--filter', 'ancestor=intellistream/sage:devel-ubuntu22.04',
                '--format', '{{.Names}}'
            ], capture=True)
            
            containers = result.stdout.strip().split('\n')
            return containers[0] if containers and containers[0] else None
        except Exception:
            return None
