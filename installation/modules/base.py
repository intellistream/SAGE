"""
Base Installation Module
=======================

Common utilities and base class for SAGE installation.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional
import threading
import time
import atexit


class Colors:
    """Terminal color codes for formatted output."""
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


class BaseInstaller:
    """Base installer class with common functionality."""
    
    def __init__(self, conda_env_name: str = "sage"):
        self.project_root = Path(__file__).parent.parent.parent.absolute()
        self.conda_env_name = conda_env_name
        self.is_ci = os.getenv('CI', '').lower() in ('true', '1', 'yes')
        self.sage_dir = Path.home() / ".sage"
        self.config_file = self.sage_dir / "config.json"
        
        # Create setup directory if not exists
        self.sage_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self.load_config()
        
        # Register cleanup
        atexit.register(self._cleanup_temp_files)
        
        # Docker script paths
        self.start_script = self.project_root / "installation" / "container_setup" / "start.sh"
    
    def _cleanup_temp_files(self):
        """Clean up temporary files on exit."""
        pass
    
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
            self.print_warning(f"Failed to save configuration: {e}")
    
    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}")
        print(f"{text.center(60)}")
        print(f"{'=' * 60}{Colors.RESET}\n")
    
    def print_success(self, text: str):
        """Print a success message."""
        print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")
    
    def print_error(self, text: str):
        """Print an error message."""
        print(f"{Colors.RED}❌ {text}{Colors.RESET}")
    
    def print_warning(self, text: str):
        """Print a warning message."""
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")
    
    def print_info(self, text: str):
        """Print an info message."""
        print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")
    
    def print_step(self, text: str):
        """Print a step message."""
        print(f"{Colors.CYAN}🔧 {text}{Colors.RESET}")
    
    def run_command_with_progress(self, cmd, description: str = "Processing", 
                                 cwd: Optional[Path] = None, env: Optional[Dict] = None) -> subprocess.CompletedProcess:
        """Run a command with a progress indicator."""
        self.print_info(f"{description}...")
        print(f"{Colors.YELLOW}⏳ This may take several minutes, please wait...{Colors.RESET}")
        
        # Progress indicator
        progress_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        progress_running = True
        
        def show_progress():
            i = 0
            while progress_running:
                char = progress_chars[i % len(progress_chars)]
                print(f"\r{Colors.YELLOW}{char} {description}...{Colors.RESET}", end="", flush=True)
                time.sleep(0.1)
                i += 1
        
        progress_thread = threading.Thread(target=show_progress)
        progress_thread.daemon = True
        progress_thread.start()
        
        try:
            result = self.run_command(cmd, cwd=cwd, check=True, capture=False, env=env)
            progress_running = False
            progress_thread.join(timeout=0.2)
            print(f"\r{Colors.GREEN}✅ {description} completed successfully!{Colors.RESET}")
            return result
        except Exception as e:
            progress_running = False
            progress_thread.join(timeout=0.2)
            print(f"\r{Colors.RED}❌ {description} failed!{Colors.RESET}")
            raise e
    
    def run_command(self, cmd, cwd: Optional[Path] = None, check: bool = True, 
                   capture: bool = False, env: Optional[Dict] = None) -> subprocess.CompletedProcess:
        """Run a shell command with proper error handling."""
        try:
            kwargs = {
                'cwd': cwd,
                'env': env or os.environ,
                'check': check
            }
            
            if capture:
                kwargs.update({'capture_output': True, 'text': True})
            
            return subprocess.run(cmd, **kwargs)
            
        except subprocess.CalledProcessError as e:
            if capture and e.stderr:
                self.print_error(f"Command failed: {' '.join(cmd)}")
                self.print_error(f"Error: {e.stderr.strip()}")
            raise
        except FileNotFoundError:
            self.print_error(f"Command not found: {cmd[0]}")
            raise
    
    def pause(self):
        """Pause for user input (skip in CI)."""
        if not self.is_ci:
            input(f"{Colors.BLUE}Press Enter to continue...{Colors.RESET}")
    
    def get_user_input(self, prompt: str, default: str = "") -> str:
        """Get user input with optional default."""
        if self.is_ci:
            return default
        try:
            result = input(f"{Colors.WHITE}{prompt}{Colors.RESET}")
            return result.strip() if result.strip() else default
        except (KeyboardInterrupt, EOFError):
            return default
    
    def confirm_action(self, prompt: str) -> bool:
        """Ask for user confirmation."""
        if self.is_ci:
            return True
        response = self.get_user_input(f"{prompt} (y/N): ", "n")
        return response.lower() in ('y', 'yes')
