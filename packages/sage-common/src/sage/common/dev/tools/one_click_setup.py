"""
One-Click Setup Tool

This tool provides automated environment setup functionality
for rapid development workflow. For testing, it uses the enhanced_test_runner.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..core.exceptions import SAGEDevToolkitError
from ..utils.sage_home import get_logs_dir, setup_project_symlinks
from .enhanced_test_runner import EnhancedTestRunner


class OneClickSetupTester:
    """Tool for automated setup and testing workflow."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
        # Get project name from path
        project_name = self.project_root.name
        
        # Set up symlink to SAGE home
        setup_project_symlinks(self.project_root, project_name)
        
        # Use .sage subdirectories for all output
        sage_link = self.project_root / '.sage'
        self.logs_dir = sage_link / 'logs'
        
        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_and_test(self, **kwargs) -> Dict[str, Any]:
        """Run complete setup and test cycle.
        
        Args:
            workers: Number of parallel workers for testing
            quick_test: Run quick tests only
            discover_only: Only discover test structure
            test_only: Skip setup, only run tests
            
        Returns:
            Dict with results including status, execution time, and phases
        """
        start_time = time.time()
        phases = {}
        
        try:
            # Phase 1: Environment setup (unless test_only)
            if not kwargs.get('test_only', False):
                console_print("📦 Setting up environment...")
                setup_result = self._setup_environment()
                phases['setup'] = setup_result
                
                if setup_result['status'] != 'success':
                    return self._build_failure_result(phases, start_time, "Setup failed")
            
            # Phase 2: Dependency installation (unless test_only)
            if not kwargs.get('test_only', False):
                console_print("🔧 Installing dependencies...")
                install_result = self._install_dependencies()
                phases['install'] = install_result
                
                if install_result['status'] != 'success':
                    return self._build_failure_result(phases, start_time, "Installation failed")
            
            # Phase 3: Test discovery and execution
            if kwargs.get('discover_only', False):
                console_print("🔍 Discovering tests...")
                test_result = self._discover_tests()
            else:
                console_print("🧪 Running tests...")
                test_result = self._run_tests(**kwargs)
            
            phases['test'] = test_result
            
            # Build final result
            total_time = time.time() - start_time
            overall_status = 'success' if all(
                phase.get('status') == 'success' for phase in phases.values()
            ) else 'failed'
            
            return {
                'status': overall_status,
                'total_execution_time': total_time,
                'phases': phases,
                'summary': self._build_summary(phases)
            }
            
        except Exception as e:
            return self._build_failure_result(phases, start_time, str(e))
    
    def _setup_environment(self) -> Dict[str, Any]:
        """Set up the development environment."""
        try:
            # Check if Python environment is properly configured
            result = subprocess.run([
                sys.executable, '-c', 
                'import sys; print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                return {
                    'status': 'failed',
                    'error': 'Python environment check failed',
                    'stderr': result.stderr
                }
            
            return {
                'status': 'success',
                'python_version': result.stdout.strip(),
                'message': 'Environment setup completed'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _install_dependencies(self) -> Dict[str, Any]:
        """Install project dependencies using requirements-dev.txt."""
        try:
            installed_components = []
            
            # Modern approach: Use requirements-dev.txt for all dependencies
            requirements_dev = self.project_root / 'requirements-dev.txt'
            if requirements_dev.exists():
                console_print("📋 Installing from requirements-dev.txt...")
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', 'requirements-dev.txt'
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode != 0:
                    return {
                        'status': 'failed',
                        'error': 'Failed to install from requirements-dev.txt',
                        'stderr': result.stderr,
                        'stdout': result.stdout
                    }
                installed_components.append('requirements-dev.txt')
                
            else:
                # Fallback: Legacy method with individual package installation
                console_print("⚠️  requirements-dev.txt not found, using legacy package installation...")
                
                # Check for pyproject.toml in root
                pyproject_file = self.project_root / 'pyproject.toml'
                if pyproject_file.exists():
                    result = subprocess.run([
                        sys.executable, '-m', 'pip', 'install', '-e', '.'
                    ], capture_output=True, text=True, cwd=self.project_root)
                    
                    if result.returncode != 0:
                        return {
                            'status': 'failed',
                            'error': 'Failed to install main package',
                            'stderr': result.stderr
                        }
                    installed_components.append('main_package')
                
                # Check for packages directory
                packages_dir = self.project_root / 'packages'
                if packages_dir.exists():
                    for package_path in packages_dir.iterdir():
                        if package_path.is_dir() and (package_path / 'pyproject.toml').exists():
                            result = subprocess.run([
                                sys.executable, '-m', 'pip', 'install', '-e', str(package_path)
                            ], capture_output=True, text=True, cwd=self.project_root)
                            
                            if result.returncode == 0:
                                installed_components.append(package_path.name)
            
            return {
                'status': 'success',
                'installed_components': installed_components,
                'method': 'requirements-dev.txt' if requirements_dev.exists() else 'legacy',
                'message': f'Installed using {"requirements-dev.txt" if requirements_dev.exists() else f"{len(installed_components)} individual packages"}'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _discover_tests(self) -> Dict[str, Any]:
        """Discover test files and structure."""
        try:
            test_files = []
            
            # Discover pytest test files
            for pattern in ['test_*.py', '*_test.py']:
                test_files.extend(list(self.project_root.rglob(pattern)))
            
            # Also check for tests directories
            for tests_dir in self.project_root.rglob('tests'):
                if tests_dir.is_dir():
                    test_files.extend(list(tests_dir.rglob('*.py')))
            
            return {
                'status': 'success',
                'test_files': [str(f.relative_to(self.project_root)) for f in test_files],
                'test_count': len(test_files),
                'message': f'Discovered {len(test_files)} test files'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _run_tests(self, **kwargs) -> Dict[str, Any]:
        """Run the test suite."""
        try:
            # Build pytest command
            cmd = [sys.executable, '-m', 'pytest']
            
            # Add options based on kwargs
            if kwargs.get('quick_test', False):
                cmd.extend(['-x', '--tb=short'])  # Stop at first failure, short traceback
            
            if kwargs.get('workers'):
                cmd.extend(['-n', str(kwargs['workers'])])  # Parallel execution
            
            # Add verbose output
            cmd.append('-v')
            
            # Run tests
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            # Parse output for summary
            output_lines = result.stdout.split('\n') if result.stdout else []
            test_summary = self._parse_test_output(output_lines)
            
            return {
                'status': 'success' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'summary': test_summary,
                'message': f'Tests completed with return code {result.returncode}'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _parse_test_output(self, output_lines: List[str]) -> Dict[str, int]:
        """Parse pytest output for test summary."""
        summary = {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0}
        
        for line in output_lines:
            if 'passed' in line and 'failed' in line:
                # Try to extract numbers from summary line
                words = line.split()
                for i, word in enumerate(words):
                    if word == 'passed' and i > 0:
                        try:
                            summary['passed'] = int(words[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif word == 'failed' and i > 0:
                        try:
                            summary['failed'] = int(words[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif word == 'skipped' and i > 0:
                        try:
                            summary['skipped'] = int(words[i-1])
                        except (ValueError, IndexError):
                            pass
        
        summary['total'] = summary['passed'] + summary['failed'] + summary['skipped']
        return summary
    
    def _build_summary(self, phases: Dict[str, Any]) -> Dict[str, Any]:
        """Build overall summary from phase results."""
        summary = {
            'phases_completed': len(phases),
            'phases_successful': sum(1 for p in phases.values() if p.get('status') == 'success'),
        }
        
        # Add test summary if available
        if 'test' in phases and 'summary' in phases['test']:
            summary.update(phases['test']['summary'])
        
        return summary
    
    def _build_failure_result(self, phases: Dict[str, Any], start_time: float, error: str) -> Dict[str, Any]:
        """Build result object for failure cases."""
        return {
            'status': 'failed',
            'total_execution_time': time.time() - start_time,
            'phases': phases,
            'error': error,
            'summary': self._build_summary(phases)
        }


def console_print(message: str, style: str = ""):
    """Simple console output - could be enhanced with rich if available."""
    print(message)
