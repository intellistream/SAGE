"""
Import Path Fixing Tool - Integrated from fix_import_paths.py

This tool automatically fixes import path errors in SAGE packages.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
from ..core.exceptions import SAGEDevToolkitError


class ImportPathFixer:
    """Tool for fixing import paths in SAGE packages."""
    
    def __init__(self, packages_root: str):
        self.packages_root = Path(packages_root)
        self.fixes_applied = []
        self.fixes_failed = []
        
        # Common path mapping rules
        self.path_mappings = {
            # Incorrect import -> Correct import
            'sage.utils.logging.custom_logger': 'sage.utils.logging.custom_logger',
            'sage.utils.llm-clients.base': 'sage.utils.llm-clients.base',
            'sage.runtime.state': 'sage.utils.persistence.state',
            'sage_ext.sage_queue': 'sage.extensions.sage_queue',
            'sage_queue': 'sage.extensions.sage_queue.python.sage_queue',
            'sage_plugins': 'sage.plugins',
        }
        
        # File patterns to check
        self.file_patterns = ['*.py']
    
    def fix_imports(self, dry_run: bool = False) -> Dict:
        """Fix import paths in all SAGE packages."""
        try:
            results = {
                'total_files_checked': 0,
                'fixes_applied': [],
                'fixes_failed': [],
                'dry_run': dry_run
            }
            
            for package_dir in self.packages_root.iterdir():
                if package_dir.is_dir() and not package_dir.name.startswith('.'):
                    self._fix_package_imports(package_dir, dry_run, results)
            
            return results
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Import path fixing failed: {e}")
    
    def _fix_package_imports(self, package_dir: Path, dry_run: bool, results: Dict):
        """Fix imports in a specific package."""
        for py_file in package_dir.rglob('*.py'):
            try:
                results['total_files_checked'] += 1
                
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Apply path mappings
                for wrong_import, correct_import in self.path_mappings.items():
                    pattern = rf'\bfrom\s+{re.escape(wrong_import)}\b'
                    replacement = f'from {correct_import}'
                    content = re.sub(pattern, replacement, content)
                    
                    pattern = rf'\bimport\s+{re.escape(wrong_import)}\b'
                    replacement = f'import {correct_import}'
                    content = re.sub(pattern, replacement, content)
                
                if content != original_content:
                    fix_info = {
                        'file': str(py_file.relative_to(self.packages_root)),
                        'changes': self._get_changes(original_content, content)
                    }
                    
                    if not dry_run:
                        with open(py_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        results['fixes_applied'].append(fix_info)
                    else:
                        fix_info['dry_run'] = True
                        results['fixes_applied'].append(fix_info)
                        
            except Exception as e:
                error_info = {
                    'file': str(py_file.relative_to(self.packages_root)),
                    'error': str(e)
                }
                results['fixes_failed'].append(error_info)
    
    def _get_changes(self, original: str, modified: str) -> List[str]:
        """Get list of changes made."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        changes = []
        for i, (orig, mod) in enumerate(zip(original_lines, modified_lines)):
            if orig != mod:
                changes.append(f"Line {i+1}: '{orig}' -> '{mod}'")
        
        return changes
