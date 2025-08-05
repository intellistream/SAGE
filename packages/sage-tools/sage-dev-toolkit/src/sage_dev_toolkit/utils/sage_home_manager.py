"""
Simple SAGE home directory manager.

This utility manages the ~/.sage directory and creates a logs symlink.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any


class SAGEHomeManager:
    """Simple manager for SAGE home directory."""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.sage_home = self.home_dir / ".sage"
        
    def setup_sage_home(self, project_root: str) -> Dict[str, Any]:
        """Set up ~/.sage directory and create logs symlink."""
        try:
            project_path = Path(project_root)
            
            # Create ~/.sage directory
            self.sage_home.mkdir(exist_ok=True)
            
            # Create logs directory in ~/.sage
            logs_dir = self.sage_home / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            # Project logs symlink path
            project_logs = project_path / "dev_reports"
            
            # Remove existing symlink or directory if it exists
            if project_logs.exists() or project_logs.is_symlink():
                if project_logs.is_symlink():
                    project_logs.unlink()
                elif project_logs.is_dir():
                    shutil.rmtree(project_logs)
                else:
                    project_logs.unlink()
            
            # Create symlink from project to ~/.sage/logs
            project_logs.symlink_to(logs_dir)
            
            return {
                'status': 'success',
                'sage_home': str(self.sage_home),
                'logs_dir': str(logs_dir),
                'symlink_created': str(project_logs),
                'message': f'Created logs symlink: {project_logs} -> {logs_dir}'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'sage_home': str(self.sage_home)
            }
    
    def check_sage_home(self) -> Dict[str, Any]:
        """Check SAGE home directory status."""
        logs_dir = self.sage_home / "logs"
        
        return {
            'sage_home_exists': self.sage_home.exists(),
            'sage_home_path': str(self.sage_home),
            'logs_dir_exists': logs_dir.exists(),
            'logs_dir_path': str(logs_dir),
            'logs_dir_size': self._get_dir_size(logs_dir) if logs_dir.exists() else 0,
            'log_files_count': len(list(logs_dir.glob('*.log'))) if logs_dir.exists() else 0
        }
    
    def clean_logs(self, older_than_days: int = 7) -> Dict[str, Any]:
        """Clean old log files."""
        try:
            logs_dir = self.sage_home / "logs"
            if not logs_dir.exists():
                return {'status': 'success', 'message': 'No logs directory found', 'files_removed': 0}
            
            import time
            current_time = time.time()
            cutoff_time = current_time - (older_than_days * 24 * 60 * 60)
            
            files_removed = 0
            for log_file in logs_dir.glob('*.log'):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    files_removed += 1
            
            return {
                'status': 'success',
                'files_removed': files_removed,
                'cutoff_days': older_than_days,
                'message': f'Removed {files_removed} log files older than {older_than_days} days'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _get_dir_size(self, path: Path) -> int:
        """Get directory size in bytes."""
        try:
            total_size = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except:
            return 0
