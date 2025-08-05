"""
VS Code Path Configuration Tool - Integrated from update_vscode_paths*.py

This tool automatically updates VS Code settings.json with Python path configurations.
"""

import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Set
from ..core.exceptions import SAGEDevToolkitError


class VSCodePathManager:
    """Tool for managing VS Code Python path configurations."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.packages_dir = self.project_root / 'packages'
        self.vscode_settings_path = self.project_root / '.vscode' / 'settings.json'
    
    def update_python_paths(self, mode: str = 'enhanced') -> Dict:
        """Update VS Code Python path configurations.
        
        Args:
            mode: 'basic' for pyproject.toml only, 'enhanced' for all Python packages
        """
        try:
            if mode == 'enhanced':
                src_paths = self._find_all_python_packages()
            else:
                src_paths = self._find_packages_with_pyproject()
            
            return self._update_settings_json(src_paths)
            
        except Exception as e:
            raise SAGEDevToolkitError(f"VS Code path update failed: {e}")
    
    def _find_packages_with_pyproject(self) -> List[str]:
        """Find packages with pyproject.toml files."""
        if not self.packages_dir.exists():
            return []
        
        src_paths = []
        pyproject_files = glob.glob(str(self.packages_dir / "**" / "pyproject.toml"), recursive=True)
        
        for pyproject_file in pyproject_files:
            package_dir = Path(pyproject_file).parent
            potential_src_paths = [
                package_dir / "src",
                package_dir / package_dir.name.replace('-', '_'),
                package_dir
            ]
            
            for src_path in potential_src_paths:
                if src_path.exists() and src_path.is_dir():
                    relative_path = src_path.relative_to(self.project_root)
                    src_paths.append(f"./{relative_path}")
                    break
        
        return src_paths
    
    def _find_all_python_packages(self) -> List[str]:
        """Find all Python packages (enhanced mode)."""
        if not self.packages_dir.exists():
            return []
        
        src_paths = set()
        
        # Method 1: Find packages with pyproject.toml
        pyproject_files = glob.glob(str(self.packages_dir / "**" / "pyproject.toml"), recursive=True)
        
        for pyproject_file in pyproject_files:
            package_dir = Path(pyproject_file).parent
            potential_src_paths = [
                package_dir / "src",
                package_dir / package_dir.name.replace('-', '_'),
                package_dir
            ]
            
            for src_path in potential_src_paths:
                if src_path.exists() and src_path.is_dir():
                    relative_path = src_path.relative_to(self.project_root)
                    src_paths.add(f"./{relative_path}")
                    break
        
        # Method 2: Find directories with __init__.py
        init_files = glob.glob(str(self.packages_dir / "**" / "__init__.py"), recursive=True)
        
        for init_file in init_files:
            package_dir = Path(init_file).parent
            # Skip __pycache__ and other special directories
            if any(part.startswith('.') or part == '__pycache__' for part in package_dir.parts):
                continue
            
            relative_path = package_dir.relative_to(self.project_root)
            src_paths.add(f"./{relative_path}")
        
        # Method 3: Find directories with Python files
        py_files = glob.glob(str(self.packages_dir / "**" / "*.py"), recursive=True)
        
        for py_file in py_files:
            py_path = Path(py_file)
            if any(part.startswith('.') or part == '__pycache__' for part in py_path.parts):
                continue
            
            package_dir = py_path.parent
            relative_path = package_dir.relative_to(self.project_root)
            src_paths.add(f"./{relative_path}")
        
        return sorted(list(src_paths))
    
    def _update_settings_json(self, src_paths: List[str]) -> Dict:
        """Update VS Code settings.json file."""
        # Ensure .vscode directory exists
        self.vscode_settings_path.parent.mkdir(exist_ok=True)
        
        # Load existing settings
        if self.vscode_settings_path.exists():
            with open(self.vscode_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        # Update Python analysis paths
        settings["python.analysis.extraPaths"] = src_paths
        
        # Also update autoImport paths for better IntelliSense
        settings["python.analysis.autoImportCompletions"] = True
        settings["python.analysis.packageIndexDepths"] = [
            {"name": "sage", "depth": 10},
            {"name": "", "depth": 2}
        ]
        
        # Write updated settings
        with open(self.vscode_settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        return {
            'settings_file': str(self.vscode_settings_path),
            'paths_added': len(src_paths),
            'paths': src_paths,
            'status': 'success'
        }
    
    def get_current_paths(self) -> Dict:
        """Get current Python paths from VS Code settings."""
        if not self.vscode_settings_path.exists():
            return {'paths': [], 'status': 'no_settings_file'}
        
        try:
            with open(self.vscode_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            return {
                'paths': settings.get('python.analysis.extraPaths', []),
                'status': 'success'
            }
        except Exception as e:
            return {'paths': [], 'status': f'error: {e}'}
