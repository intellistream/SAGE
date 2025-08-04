"""
One-Click Setup and Test Tool - Integrated from one_click_setup_and_test.py

This tool provides one-click environment setup and testing capabilities.
"""

import os
import sys
import subprocess
import shutil
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from ..core.exceptions import SAGEDevToolkitError


class OneClickSetupTester:
    """Tool for one-click environment setup and testing."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.test_env_dir = self.project_root / 'test_env'
        self.packages_dir = self.project_root / 'packages'
        self.reports_dir = self.project_root / 'dev_reports'
        
    def setup_and_test(self, 
                      workers: Optional[int] = None,
                      quick_test: bool = False,
                      discover_only: bool = False,
                      test_only: bool = False) -> Dict:
        """Run complete setup and test cycle."""
        try:
            start_time = time.time()
            results = {
                'start_time': datetime.now().isoformat(),
                'phases': {},
                'total_execution_time': 0,
                'status': 'running'
            }
            
            if not test_only:
                # Phase 1: Environment setup
                setup_result = self._setup_environment()
                results['phases']['setup'] = setup_result
                
                if setup_result['status'] != 'success':
                    results['status'] = 'failed'
                    return results
            
            if not discover_only:
                # Phase 2: Package installation
                if not test_only:
                    install_result = self._install_packages()
                    results['phases']['install'] = install_result
                    
                    if install_result['status'] != 'success':
                        results['status'] = 'failed'
                        return results
                
                # Phase 3: Test execution
                test_result = self._run_tests(workers, quick_test)
                results['phases']['test'] = test_result
                
                if test_result['status'] != 'success':
                    results['status'] = 'failed'
                    return results
            else:
                # Just discover test structure
                discover_result = self._discover_tests()
                results['phases']['discover'] = discover_result
            
            # Phase 4: Report generation
            report_result = self._generate_report(results)
            results['phases']['report'] = report_result
            
            results['total_execution_time'] = time.time() - start_time
            results['status'] = 'success'
            
            return results
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Setup and test failed: {e}")
    
    def _setup_environment(self) -> Dict:
        """Setup clean test environment."""
        try:
            # Remove existing test environment
            if self.test_env_dir.exists():
                shutil.rmtree(self.test_env_dir)
            
            # Create virtual environment
            subprocess.run([
                sys.executable, '-m', 'venv', str(self.test_env_dir)
            ], check=True, capture_output=True)
            
            # Get python and pip paths
            if os.name == 'nt':  # Windows
                python_exe = self.test_env_dir / 'Scripts' / 'python.exe'
                pip_exe = self.test_env_dir / 'Scripts' / 'pip.exe'
            else:  # Unix-like
                python_exe = self.test_env_dir / 'bin' / 'python'
                pip_exe = self.test_env_dir / 'bin' / 'pip'
            
            # Upgrade pip
            subprocess.run([
                str(pip_exe), 'install', '--upgrade', 'pip'
            ], check=True, capture_output=True)
            
            return {
                'status': 'success',
                'python_exe': str(python_exe),
                'pip_exe': str(pip_exe),
                'environment_path': str(self.test_env_dir)
            }
            
        except subprocess.CalledProcessError as e:
            return {
                'status': 'failed',
                'error': f"Environment setup failed: {e}",
                'stderr': e.stderr.decode() if e.stderr else None
            }
    
    def _install_packages(self) -> Dict:
        """Install all SAGE packages."""
        try:
            # Get pip executable
            if os.name == 'nt':
                pip_exe = self.test_env_dir / 'Scripts' / 'pip.exe'
            else:
                pip_exe = self.test_env_dir / 'bin' / 'pip'
            
            installed_packages = []
            failed_packages = []
            
            # Define package installation order (based on dependencies)
            package_order = [
                'sage-utils',
                'sage-core', 
                'sage-lib',
                'sage-extensions',
                'sage-plugins',
                'sage-service',
                'sage-cli'
            ]
            
            for package_name in package_order:
                package_path = self.packages_dir / package_name
                if package_path.exists():
                    try:
                        # Install in development mode
                        subprocess.run([
                            str(pip_exe), 'install', '-e', str(package_path)
                        ], check=True, capture_output=True)
                        installed_packages.append(package_name)
                    except subprocess.CalledProcessError as e:
                        failed_packages.append({
                            'package': package_name,
                            'error': e.stderr.decode() if e.stderr else str(e)
                        })
            
            return {
                'status': 'success',
                'installed_packages': installed_packages,
                'failed_packages': failed_packages,
                'total_installed': len(installed_packages)
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': f"Package installation failed: {e}"
            }
    
    def _run_tests(self, workers: Optional[int], quick_test: bool) -> Dict:
        """Run test suite."""
        try:
            # Get python executable
            if os.name == 'nt':
                python_exe = self.test_env_dir / 'Scripts' / 'python.exe'
            else:
                python_exe = self.test_env_dir / 'bin' / 'python'
            
            # Build pytest command
            cmd = [str(python_exe), '-m', 'pytest']
            
            if workers:
                cmd.extend(['-n', str(workers)])
            
            if quick_test:
                cmd.extend(['-m', 'not slow'])
            
            # Add coverage reporting
            cmd.extend(['--cov=sage', '--cov-report=json', '--cov-report=html'])
            
            # Run tests
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            
            return {
                'status': 'success' if result.returncode == 0 else 'failed',
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': f"Test execution failed: {e}"
            }
    
    def _discover_tests(self) -> Dict:
        """Discover test structure."""
        try:
            test_files = []
            test_dirs = []
            
            for package_dir in self.packages_dir.iterdir():
                if package_dir.is_dir() and not package_dir.name.startswith('.'):
                    # Look for test directories
                    for test_pattern in ['test', 'tests']:
                        test_dir = package_dir / test_pattern
                        if test_dir.exists():
                            test_dirs.append(str(test_dir.relative_to(self.project_root)))
                            
                            # Count test files
                            for test_file in test_dir.rglob('test_*.py'):
                                test_files.append(str(test_file.relative_to(self.project_root)))
            
            return {
                'status': 'success',
                'test_directories': test_dirs,
                'test_files': test_files,
                'total_test_files': len(test_files)
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': f"Test discovery failed: {e}"
            }
    
    def _generate_report(self, results: Dict) -> Dict:
        """Generate comprehensive report."""
        try:
            self.reports_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = self.reports_dir / f'setup_test_report_{timestamp}.json'
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            return {
                'status': 'success',
                'report_file': str(report_file),
                'timestamp': timestamp
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': f"Report generation failed: {e}"
            }
