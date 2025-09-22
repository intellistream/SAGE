"""
Commercial Package Manager - Integrated from scripts/commercial-package-manager.py

This tool manages commercial SAGE packages and their deployment.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import json
from ..core.exceptions import SAGEDevToolkitError


class CommercialPackageManager:
    """Tool for managing commercial SAGE packages."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.commercial_path = self.project_root / "packages" / "commercial"
        
        # Define commercial packages
        self.packages = {
            "sage-kernel": {
                "path": self.commercial_path / "sage-kernel",
                "description": "High-performance kernel infrastructure",
                "components": ["sage_queue"],
                "dependencies": ["sage-kernel", "sage-utils"]
            },
            "sage-middleware": {
                "path": self.commercial_path / "sage-middleware", 
                "description": "Database and storage middleware",
                "components": ["sage_db"],
                "dependencies": ["sage-kernel", "sage-utils"]
            },
            "sage-userspace": {
                "path": self.commercial_path / "sage-userspace",
                "description": "User-space runtime components", 
                "components": ["sage_runtime"],
                "dependencies": ["sage-kernel", "sage-middleware"]
            }
        }
    
    def list_commercial_packages(self) -> Dict[str, Any]:
        """List all commercial packages with their status."""
        try:
            package_list = []
            
            for name, info in self.packages.items():
                package_info = {
                    'name': name,
                    'description': info['description'],
                    'components': info['components'],
                    'dependencies': info['dependencies'],
                    'path': str(info['path']),
                    'exists': info['path'].exists(),
                    'status': self._get_package_status(info['path'])
                }
                package_list.append(package_info)
            
            return {
                'packages': package_list,
                'total_packages': len(package_list),
                'commercial_path': str(self.commercial_path),
                'status': 'success'
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Commercial package listing failed: {e}")
    
    def install_commercial_package(self, package_name: str, dev_mode: bool = True) -> Dict[str, Any]:
        """Install a commercial package."""
        try:
            if package_name not in self.packages:
                raise SAGEDevToolkitError(f"Unknown commercial package: {package_name}")
            
            package_info = self.packages[package_name]
            package_path = package_info['path']
            
            if not package_path.exists():
                raise SAGEDevToolkitError(f"Commercial package directory not found: {package_path}")
            
            # Install dependencies first
            for dep in package_info['dependencies']:
                if dep in self.packages:
                    dep_result = self.install_commercial_package(dep, dev_mode)
                    if dep_result['status'] != 'success':
                        return {
                            'package': package_name,
                            'status': 'failed',
                            'error': f"Failed to install dependency: {dep}"
                        }
            
            # Install the package
            cmd = [sys.executable, '-m', 'pip', 'install']
            if dev_mode:
                cmd.append('-e')
            cmd.append(str(package_path))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {
                'package': package_name,
                'status': 'success' if result.returncode == 0 else 'failed',
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(cmd)
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Commercial package installation failed: {e}")
    
    def build_commercial_extensions(self, package_name: str = None) -> Dict[str, Any]:
        """Build C++ extensions for commercial packages."""
        try:
            if package_name:
                # Build specific package
                if package_name not in self.packages:
                    raise SAGEDevToolkitError(f"Unknown commercial package: {package_name}")
                
                package_path = self.packages[package_name]['path']
                return self._build_package_extensions(package_name, package_path)
            else:
                # Build all packages
                results = {}
                for name, info in self.packages.items():
                    if info['path'].exists():
                        results[name] = self._build_package_extensions(name, info['path'])
                
                return {
                    'results': results,
                    'total_packages': len(results),
                    'status': 'success'
                }
                
        except Exception as e:
            raise SAGEDevToolkitError(f"Extension building failed: {e}")
    
    def check_commercial_status(self) -> Dict[str, Any]:
        """Check status of all commercial packages."""
        try:
            status_info = {
                'commercial_path_exists': self.commercial_path.exists(),
                'packages': {},
                'summary': {
                    'total': len(self.packages),
                    'available': 0,
                    'installed': 0,
                    'missing': 0
                }
            }
            
            for name, info in self.packages.items():
                package_status = {
                    'exists': info['path'].exists(),
                    'installed': self._is_package_installed(name),
                    'components_built': self._check_components_built(info),
                    'path': str(info['path'])
                }
                
                status_info['packages'][name] = package_status
                
                if package_status['exists']:
                    status_info['summary']['available'] += 1
                else:
                    status_info['summary']['missing'] += 1
                
                if package_status['installed']:
                    status_info['summary']['installed'] += 1
            
            return status_info
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Commercial status check failed: {e}")
    
    def _get_package_status(self, package_path: Path) -> str:
        """Get status of a package."""
        if not package_path.exists():
            return 'missing'
        
        # Check if it has pyproject.toml or setup.py
        if (package_path / 'pyproject.toml').exists() or (package_path / 'setup.py').exists():
            return 'ready'
        
        return 'incomplete'
    
    def _build_package_extensions(self, package_name: str, package_path: Path) -> Dict[str, Any]:
        """Build extensions for a specific package."""
        try:
            # Look for build script
            build_script = package_path / 'build_extensions.sh'
            if build_script.exists():
                result = subprocess.run([
                    'bash', str(build_script)
                ], capture_output=True, text=True, cwd=str(package_path))
                
                return {
                    'package': package_name,
                    'status': 'success' if result.returncode == 0 else 'failed',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            else:
                # Try standard Python build
                result = subprocess.run([
                    sys.executable, 'setup.py', 'build_ext', '--inplace'
                ], capture_output=True, text=True, cwd=str(package_path))
                
                return {
                    'package': package_name,
                    'status': 'success' if result.returncode == 0 else 'failed',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
        except Exception as e:
            return {
                'package': package_name,
                'status': 'failed',
                'error': str(e)
            }
    
    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed."""
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'show', package_name.replace('-', '_')
            ], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def _check_components_built(self, package_info: Dict) -> bool:
        """Check if package components are built."""
        package_path = package_info['path']
        if not package_path.exists():
            return False
        
        # Check for built extensions
        for component in package_info['components']:
            # Look for .so files (Unix) or .pyd files (Windows)
            so_files = list(package_path.rglob(f"{component}*.so"))
            pyd_files = list(package_path.rglob(f"{component}*.pyd"))
            
            if not (so_files or pyd_files):
                return False
        
        return True
