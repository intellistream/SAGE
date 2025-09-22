"""
Enhanced SAGE Package Manager - Integrated from scripts/sage-package-manager.py

This tool provides comprehensive package management for the SAGE monorepo.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Optional
import json
from ..core.exceptions import SAGEDevToolkitError


class EnhancedPackageManager:
    """Enhanced SAGE package manager with dependency resolution."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.packages_dir = self.project_root / 'packages'
        
        # Define packages and their dependencies
        self.packages = {
            'sage-common': {
                'path': self.packages_dir / 'sage-common',
                'namespace': 'sage.common',
                'dependencies': [],
                'description': 'Common utilities and base framework'
            },
            'sage-kernel': {
                'path': self.packages_dir / 'sage-kernel',
                'namespace': 'sage.core',
                'dependencies': ['sage-common'],
                'description': 'Core framework components'
            },
            'sage-middleware': {
                'path': self.packages_dir / 'sage-middleware',
                'namespace': 'sage.middleware',
                'dependencies': ['sage-common', 'sage-kernel'],
                'description': 'Middleware and API services'
            },
            'sage-libs': {
                'path': self.packages_dir / 'sage-libs',
                'namespace': 'sage.libs',
                'dependencies': ['sage-common'],
                'description': 'Application libraries and examples'
            },
            'sage': {
                'path': self.packages_dir / 'sage',
                'namespace': 'sage',
                'dependencies': ['sage-common', 'sage-kernel', 'sage-middleware', 'sage-libs'],
                'description': 'Meta package - all SAGE components'
            },
        }
    
    def list_packages(self) -> Dict:
        """List all SAGE packages with their status."""
        try:
            package_list = []
            
            for name, info in self.packages.items():
                package_info = {
                    'name': name,
                    'description': info['description'],
                    'namespace': info['namespace'],
                    'dependencies': info['dependencies'],
                    'path': str(info['path']),
                    'exists': info['path'].exists(),
                    'installed': self._is_package_installed(name),
                    'version': self._get_package_version(info['path'])
                }
                package_list.append(package_info)
            
            return {
                'packages': package_list,
                'total_packages': len(package_list),
                'status': 'success'
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Package listing failed: {e}")
    
    def install_package(self, package_name: str, dev_mode: bool = True, force: bool = False) -> Dict:
        """Install a specific package with its dependencies."""
        try:
            if package_name not in self.packages:
                raise SAGEDevToolkitError(f"Unknown package: {package_name}")
            
            # Get installation order
            install_order = self._get_install_order(package_name)
            
            installed = []
            failed = []
            
            for pkg_name in install_order:
                try:
                    result = self._install_single_package(pkg_name, dev_mode, force)
                    if result['status'] == 'success':
                        installed.append(pkg_name)
                    else:
                        failed.append({
                            'package': pkg_name,
                            'error': result.get('error', 'Unknown error')
                        })
                except Exception as e:
                    failed.append({
                        'package': pkg_name,
                        'error': str(e)
                    })
            
            return {
                'target_package': package_name,
                'install_order': install_order,
                'installed': installed,
                'failed': failed,
                'status': 'success' if not failed else 'partial'
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Package installation failed: {e}")
    
    def install_all_packages(self, dev_mode: bool = True, force: bool = False) -> Dict:
        """Install all packages in dependency order."""
        try:
            install_order = self._get_full_install_order()
            
            installed = []
            failed = []
            
            for pkg_name in install_order:
                try:
                    result = self._install_single_package(pkg_name, dev_mode, force)
                    if result['status'] == 'success':
                        installed.append(pkg_name)
                    else:
                        failed.append({
                            'package': pkg_name,
                            'error': result.get('error', 'Unknown error')
                        })
                except Exception as e:
                    failed.append({
                        'package': pkg_name,
                        'error': str(e)
                    })
            
            return {
                'install_order': install_order,
                'installed': installed,
                'failed': failed,
                'total_attempted': len(install_order),
                'total_successful': len(installed),
                'status': 'success' if not failed else 'partial'
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Full installation failed: {e}")
    
    def uninstall_package(self, package_name: str) -> Dict:
        """Uninstall a specific package."""
        try:
            if package_name not in self.packages:
                raise SAGEDevToolkitError(f"Unknown package: {package_name}")
            
            # Use pip to uninstall
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'uninstall', 
                package_name.replace('-', '_'), '-y'
            ], capture_output=True, text=True)
            
            return {
                'package': package_name,
                'status': 'success' if result.returncode == 0 else 'failed',
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Package uninstallation failed: {e}")
    
    def build_package(self, package_name: str) -> Dict:
        """Build a specific package."""
        try:
            if package_name not in self.packages:
                raise SAGEDevToolkitError(f"Unknown package: {package_name}")
            
            package_path = self.packages[package_name]['path']
            
            if not package_path.exists():
                raise SAGEDevToolkitError(f"Package directory not found: {package_path}")
            
            # Build the package
            result = subprocess.run([
                sys.executable, '-m', 'build', str(package_path)
            ], capture_output=True, text=True, cwd=str(package_path))
            
            return {
                'package': package_name,
                'status': 'success' if result.returncode == 0 else 'failed',
                'stdout': result.stdout,
                'stderr': result.stderr,
                'package_path': str(package_path)
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Package build failed: {e}")
    
    def check_dependencies(self) -> Dict:
        """Check package dependencies and detect issues."""
        try:
            issues = []
            dependency_graph = {}
            
            for pkg_name, pkg_info in self.packages.items():
                dependency_graph[pkg_name] = pkg_info['dependencies']
                
                # Check if dependencies exist
                for dep in pkg_info['dependencies']:
                    if dep not in self.packages:
                        issues.append({
                            'type': 'missing_dependency',
                            'package': pkg_name,
                            'missing_dependency': dep
                        })
                
                # Check if package directory exists
                if not pkg_info['path'].exists():
                    issues.append({
                        'type': 'missing_package_directory',
                        'package': pkg_name,
                        'path': str(pkg_info['path'])
                    })
            
            # Check for circular dependencies
            circular_deps = self._detect_circular_dependencies(dependency_graph)
            for cycle in circular_deps:
                issues.append({
                    'type': 'circular_dependency',
                    'cycle': cycle
                })
            
            return {
                'dependency_graph': dependency_graph,
                'issues': issues,
                'has_issues': len(issues) > 0,
                'status': 'success'
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Dependency check failed: {e}")
    
    def _get_install_order(self, package_name: str) -> List[str]:
        """Get installation order for a package and its dependencies."""
        def dfs(pkg, visited, order):
            if pkg in visited:
                return
            visited.add(pkg)
            
            for dep in self.packages.get(pkg, {}).get('dependencies', []):
                dfs(dep, visited, order)
            
            order.append(pkg)
        
        visited = set()
        order = []
        dfs(package_name, visited, order)
        return order
    
    def _get_full_install_order(self) -> List[str]:
        """Get installation order for all packages."""
        def dfs(pkg, visited, order):
            if pkg in visited:
                return
            visited.add(pkg)
            
            for dep in self.packages.get(pkg, {}).get('dependencies', []):
                dfs(dep, visited, order)
            
            if pkg not in order:
                order.append(pkg)
        
        visited = set()
        order = []
        
        for pkg_name in self.packages:
            dfs(pkg_name, visited, order)
        
        return order
    
    def _install_single_package(self, package_name: str, dev_mode: bool, force: bool) -> Dict:
        """Install a single package."""
        package_path = self.packages[package_name]['path']
        
        if not package_path.exists():
            return {
                'status': 'failed',
                'error': f"Package directory not found: {package_path}"
            }
        
        cmd = [sys.executable, '-m', 'pip', 'install']
        if dev_mode:
            cmd.append('-e')
        if force:
            cmd.append('--force-reinstall')
        cmd.append(str(package_path))
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            'status': 'success' if result.returncode == 0 else 'failed',
            'stdout': result.stdout,
            'stderr': result.stderr,
            'command': ' '.join(cmd)
        }
    
    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed."""
        try:
            # Convert sage-* package names to isage-* format for pip
            pip_package_name = package_name.replace('sage-', 'isage-')
            if package_name == 'sage':
                pip_package_name = 'isage'
            
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'show', pip_package_name
            ], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def _get_package_version(self, package_path: Path) -> str:
        """Get package version from pyproject.toml or setup.py."""
        try:
            pyproject_file = package_path / 'pyproject.toml'
            if pyproject_file.exists():
                with open(pyproject_file, 'r') as f:
                    content = f.read()
                    # Simple regex to extract version
                    import re
                    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1)
            return 'unknown'
        except:
            return 'unknown'
    
    def _detect_circular_dependencies(self, dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        def dfs(node, path, visited, cycles):
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for dep in dependency_graph.get(node, []):
                dfs(dep, path.copy(), visited, cycles)
        
        cycles = []
        visited = set()
        
        for pkg in dependency_graph:
            if pkg not in visited:
                dfs(pkg, [], visited, cycles)
        
        return cycles
