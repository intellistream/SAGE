"""
SAGE Home Directory Manager

This module manages the ~/.sage/ directory structure and creates
appropriate symlinks to keep the source repository clean.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

from ..core.exceptions import SAGEDevToolkitError


class SAGEHomeManager:
    """Manages ~/.sage/ directory structure and symlinks."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.sage_home = Path.home() / ".sage"
        
        # Define directory structure
        self.directories = {
            'cache': self.sage_home / 'cache',
            'logs': self.sage_home / 'logs', 
            'reports': self.sage_home / 'reports',
            'temp': self.sage_home / 'temp',
            'test_results': self.sage_home / 'test_results',
            'coverage': self.sage_home / 'coverage',
            'build_artifacts': self.sage_home / 'build_artifacts',
            'config_backup': self.sage_home / 'config_backup',
            'projects': self.sage_home / 'projects'
        }
        
        # Project-specific subdirectory
        project_name = self.project_root.name
        self.project_sage_dir = self.directories['projects'] / project_name
        
        # Project-specific subdirectories
        self.project_dirs = {
            'logs': self.project_sage_dir / 'logs',
            'reports': self.project_sage_dir / 'reports', 
            'temp': self.project_sage_dir / 'temp',
            'test_results': self.project_sage_dir / 'test_results',
            'coverage': self.project_sage_dir / 'coverage',
            'build': self.project_sage_dir / 'build',
            'cache': self.project_sage_dir / 'cache'
        }
    
    def setup_sage_home(self) -> Dict[str, str]:
        """Set up the ~/.sage/ directory structure."""
        try:
            results = {
                'created_dirs': [],
                'existing_dirs': [],
                'symlinks_created': [],
                'symlinks_existing': []
            }
            
            # Create main directories
            for name, path in self.directories.items():
                if path.exists():
                    results['existing_dirs'].append(str(path))
                else:
                    path.mkdir(parents=True, exist_ok=True)
                    results['created_dirs'].append(str(path))
            
            # Create project-specific directories
            for name, path in self.project_dirs.items():
                if path.exists():
                    results['existing_dirs'].append(str(path))
                else:
                    path.mkdir(parents=True, exist_ok=True)
                    results['created_dirs'].append(str(path))
            
            # Create symlinks in project repository
            symlink_results = self._create_project_symlinks()
            results['symlinks_created'].extend(symlink_results['created'])
            results['symlinks_existing'].extend(symlink_results['existing'])
            
            # Create configuration file
            self._create_sage_config()
            
            return results
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Failed to setup SAGE home: {e}")
    
    def _create_project_symlinks(self) -> Dict[str, List[str]]:
        """Create symlinks in project repository pointing to ~/.sage/."""
        results = {
            'created': [],
            'existing': []
        }
        
        # Define symlink mappings (repo_path -> sage_path)
        symlinks = {
            'dev_reports': self.project_dirs['reports'],
            'test_logs': self.project_dirs['logs'], 
            'test_results': self.project_dirs['test_results'],
            'coverage_reports': self.project_dirs['coverage'],
            '.sage_temp': self.project_dirs['temp'],
            '.sage_cache': self.project_dirs['cache'],
            'build_outputs': self.project_dirs['build']
        }
        
        for repo_name, sage_path in symlinks.items():
            repo_path = self.project_root / repo_name
            
            try:
                if repo_path.exists():
                    if repo_path.is_symlink():
                        # Check if symlink points to correct location
                        if repo_path.resolve() == sage_path.resolve():
                            results['existing'].append(f"{repo_name} -> {sage_path}")
                            continue
                        else:
                            # Remove incorrect symlink
                            repo_path.unlink()
                    elif repo_path.is_dir():
                        # Move existing directory to sage home and create symlink
                        if sage_path.exists():
                            shutil.rmtree(sage_path)
                        shutil.move(str(repo_path), str(sage_path))
                    elif repo_path.is_file():
                        # Move existing file to sage home
                        if sage_path.exists():
                            sage_path.unlink()
                        shutil.move(str(repo_path), str(sage_path))
                
                # Create symlink
                repo_path.symlink_to(sage_path)
                results['created'].append(f"{repo_name} -> {sage_path}")
                
            except Exception as e:
                print(f"Warning: Could not create symlink {repo_name}: {e}")
        
        return results
    
    def _create_sage_config(self) -> None:
        """Create SAGE configuration file."""
        config_file = self.sage_home / 'config.json'
        
        config = {
            'version': '1.0.0',
            'created': datetime.now().isoformat(),
            'projects': {
                self.project_root.name: {
                    'path': str(self.project_root),
                    'sage_dir': str(self.project_sage_dir),
                    'last_used': datetime.now().isoformat()
                }
            },
            'global_settings': {
                'auto_cleanup_days': 30,
                'max_log_size_mb': 100,
                'max_cache_size_mb': 500
            }
        }
        
        # Update existing config if it exists
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    existing_config = json.load(f)
                
                # Update project info
                existing_config['projects'][self.project_root.name] = config['projects'][self.project_root.name]
                config = existing_config
                
            except Exception as e:
                print(f"Warning: Could not read existing config: {e}")
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def cleanup_old_files(self, days_old: int = 30) -> Dict[str, int]:
        """Clean up old files in SAGE home directory."""
        try:
            cleanup_stats = {
                'files_removed': 0,
                'dirs_removed': 0,
                'space_freed_mb': 0
            }
            
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            
            for dir_path in [self.project_dirs['temp'], self.project_dirs['cache']]:
                if dir_path.exists():
                    for item in dir_path.rglob('*'):
                        try:
                            if item.stat().st_mtime < cutoff_time:
                                if item.is_file():
                                    size_mb = item.stat().st_size / (1024 * 1024)
                                    item.unlink()
                                    cleanup_stats['files_removed'] += 1
                                    cleanup_stats['space_freed_mb'] += size_mb
                                elif item.is_dir() and not any(item.iterdir()):
                                    item.rmdir()
                                    cleanup_stats['dirs_removed'] += 1
                        except Exception as e:
                            print(f"Warning: Could not remove {item}: {e}")
            
            return cleanup_stats
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Cleanup failed: {e}")
    
    def get_directory_info(self) -> Dict[str, Dict]:
        """Get information about SAGE home directories."""
        try:
            info = {}
            
            for name, path in {**self.directories, **self.project_dirs}.items():
                if path.exists():
                    # Calculate directory size
                    total_size = 0
                    file_count = 0
                    
                    for item in path.rglob('*'):
                        if item.is_file():
                            try:
                                total_size += item.stat().st_size
                                file_count += 1
                            except:
                                pass
                    
                    info[name] = {
                        'path': str(path),
                        'exists': True,
                        'size_mb': round(total_size / (1024 * 1024), 2),
                        'file_count': file_count,
                        'last_modified': datetime.fromtimestamp(
                            path.stat().st_mtime
                        ).isoformat() if path.exists() else None
                    }
                else:
                    info[name] = {
                        'path': str(path),
                        'exists': False,
                        'size_mb': 0,
                        'file_count': 0,
                        'last_modified': None
                    }
            
            return info
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Failed to get directory info: {e}")
    
    def verify_symlinks(self) -> Dict[str, bool]:
        """Verify that all symlinks are properly set up."""
        try:
            symlink_status = {}
            
            expected_symlinks = {
                'dev_reports': self.project_dirs['reports'],
                'test_logs': self.project_dirs['logs'],
                'test_results': self.project_dirs['test_results'], 
                'coverage_reports': self.project_dirs['coverage'],
                '.sage_temp': self.project_dirs['temp'],
                '.sage_cache': self.project_dirs['cache'],
                'build_outputs': self.project_dirs['build']
            }
            
            for name, expected_target in expected_symlinks.items():
                repo_path = self.project_root / name
                
                if repo_path.exists() and repo_path.is_symlink():
                    actual_target = repo_path.resolve()
                    expected_resolved = expected_target.resolve()
                    symlink_status[name] = actual_target == expected_resolved
                else:
                    symlink_status[name] = False
            
            return symlink_status
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Symlink verification failed: {e}")
    
    def repair_symlinks(self) -> Dict[str, str]:
        """Repair broken symlinks."""
        try:
            repair_results = self._create_project_symlinks()
            return {
                'repaired_symlinks': repair_results['created'],
                'status': 'success'
            }
        except Exception as e:
            raise SAGEDevToolkitError(f"Symlink repair failed: {e}")
    
    def remove_sage_integration(self) -> Dict[str, List[str]]:
        """Remove SAGE home integration (for cleanup/uninstall)."""
        try:
            results = {
                'removed_symlinks': [],
                'moved_back_dirs': [],
                'warnings': []
            }
            
            # Remove symlinks and move data back to project
            symlinks_to_remove = [
                'dev_reports', 'test_logs', 'test_results', 
                'coverage_reports', '.sage_temp', '.sage_cache', 'build_outputs'
            ]
            
            for name in symlinks_to_remove:
                repo_path = self.project_root / name
                sage_path = self.project_dirs.get(name.replace('.sage_', ''), 
                                                 self.project_dirs.get(name.replace('_reports', '').replace('_logs', 'logs').replace('_results', 'test_results')))
                
                try:
                    if repo_path.is_symlink():
                        repo_path.unlink()
                        results['removed_symlinks'].append(name)
                        
                        # Move data back if it exists in sage home
                        if sage_path and sage_path.exists():
                            shutil.move(str(sage_path), str(repo_path))
                            results['moved_back_dirs'].append(name)
                            
                except Exception as e:
                    results['warnings'].append(f"Could not process {name}: {e}")
            
            return results
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Failed to remove SAGE integration: {e}")
