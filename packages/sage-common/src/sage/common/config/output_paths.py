"""
SAGE Output Path Configuration

This module provides a centralized configuration system for all output paths in SAGE.
All intermediate results, logs, outputs, and temporary files should use this system
to ensure consistent placement in the .sage directory.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Union
from functools import lru_cache


class SageOutputPaths:
    """Centralized configuration for SAGE output paths."""
    
    def __init__(self, project_root: Optional[Union[str, Path]] = None):
        """
        Initialize SAGE output paths.
        
        Args:
            project_root: Project root directory. If None, will auto-detect.
        """
        if project_root is None:
            self.project_root = self._find_project_root()
        else:
            self.project_root = Path(project_root).resolve()
        
        # Main .sage directory (symlink to ~/.sage)
        self.sage_dir = self.project_root / ".sage"
        
        # Ensure .sage directory and subdirectories exist
        self._ensure_sage_structure()
    
    def _find_project_root(self) -> Path:
        """Find the SAGE project root directory."""
        current = Path.cwd()
        
        # Look for SAGE project markers
        while current != current.parent:
            if any((current / marker).exists() for marker in [
                "packages/sage-kernel",
                "packages/sage-common", 
                "_version.py",
                "quickstart.sh"
            ]):
                return current
            current = current.parent
        
        # Fallback to current directory
        return Path.cwd()
    
    def _ensure_sage_structure(self):
        """Ensure .sage directory and required subdirectories exist."""
        # Standard subdirectories in .sage
        subdirs = [
            "logs",
            "output", 
            "temp",
            "cache",
            "reports",
            "coverage",
            "test_logs",
            "experiments",
            "issues"
        ]
        
        # Create .sage symlink if it doesn't exist
        if not self.sage_dir.exists():
            home_sage = Path.home() / ".sage"
            home_sage.mkdir(exist_ok=True)
            self.sage_dir.symlink_to(home_sage)
        
        # Ensure subdirectories exist
        for subdir in subdirs:
            (self.sage_dir / subdir).mkdir(exist_ok=True)
    
    @property
    def logs_dir(self) -> Path:
        """Get the logs directory."""
        return self.sage_dir / "logs"
    
    @property
    def output_dir(self) -> Path:
        """Get the output directory."""
        return self.sage_dir / "output"
    
    @property
    def temp_dir(self) -> Path:
        """Get the temporary files directory."""
        return self.sage_dir / "temp"
    
    @property
    def cache_dir(self) -> Path:
        """Get the cache directory."""
        return self.sage_dir / "cache"
    
    @property
    def reports_dir(self) -> Path:
        """Get the reports directory."""
        return self.sage_dir / "reports"
    
    @property
    def coverage_dir(self) -> Path:
        """Get the coverage directory."""
        return self.sage_dir / "coverage"
    
    @property
    def test_logs_dir(self) -> Path:
        """Get the test logs directory."""
        return self.sage_dir / "test_logs"
    
    @property
    def experiments_dir(self) -> Path:
        """Get the experiments directory."""
        return self.sage_dir / "experiments"
    
    @property
    def issues_dir(self) -> Path:
        """Get the issues directory."""
        return self.sage_dir / "issues"
    
    def get_log_file(self, name: str, subdir: Optional[str] = None) -> Path:
        """
        Get a log file path.
        
        Args:
            name: Log file name
            subdir: Optional subdirectory within logs
            
        Returns:
            Path to log file
        """
        if subdir:
            log_dir = self.logs_dir / subdir
            log_dir.mkdir(exist_ok=True)
            return log_dir / name
        return self.logs_dir / name
    
    def get_output_file(self, name: str, subdir: Optional[str] = None) -> Path:
        """
        Get an output file path.
        
        Args:
            name: Output file name
            subdir: Optional subdirectory within output
            
        Returns:
            Path to output file
        """
        if subdir:
            output_dir = self.output_dir / subdir
            output_dir.mkdir(parents=True, exist_ok=True)
            return output_dir / name
        return self.output_dir / name
    
    def get_temp_file(self, name: str, subdir: Optional[str] = None) -> Path:
        """
        Get a temporary file path.
        
        Args:
            name: Temp file name
            subdir: Optional subdirectory within temp
            
        Returns:
            Path to temp file
        """
        if subdir:
            temp_dir = self.temp_dir / subdir
            temp_dir.mkdir(parents=True, exist_ok=True)
            return temp_dir / name
        return self.temp_dir / name
    
    def get_cache_file(self, name: str, subdir: Optional[str] = None) -> Path:
        """
        Get a cache file path.
        
        Args:
            name: Cache file name
            subdir: Optional subdirectory within cache
            
        Returns:
            Path to cache file
        """
        if subdir:
            cache_dir = self.cache_dir / subdir
            cache_dir.mkdir(parents=True, exist_ok=True)
            return cache_dir / name
        return self.cache_dir / name
    
    def migrate_existing_outputs(self):
        """
        Migrate existing output files from project root to .sage directory.
        
        This method will move files from:
        - logs/ -> .sage/logs/
        - output/ -> .sage/output/
        """
        migrations = [
            (self.project_root / "logs", self.logs_dir),
            (self.project_root / "output", self.output_dir)
        ]
        
        for src, dst in migrations:
            if src.exists() and src != dst:
                print(f"Migrating {src} -> {dst}")
                
                # Ensure destination directory exists
                dst.mkdir(parents=True, exist_ok=True)
                
                # Move all files and subdirectories
                for item in src.iterdir():
                    dst_item = dst / item.name
                    if item.is_dir():
                        if dst_item.exists():
                            # Merge directories
                            shutil.copytree(item, dst_item, dirs_exist_ok=True)
                            shutil.rmtree(item)
                        else:
                            shutil.move(str(item), str(dst_item))
                    else:
                        if dst_item.exists():
                            # Backup existing file
                            backup_name = f"{dst_item.name}.backup"
                            dst_item.rename(dst_item.parent / backup_name)
                        shutil.move(str(item), str(dst_item))
                
                # Remove empty source directory
                try:
                    src.rmdir()
                except OSError:
                    print(f"Warning: Could not remove {src} (not empty)")


# Global instance for easy access
@lru_cache(maxsize=1)
def get_sage_paths(project_root: Optional[Union[str, Path]] = None) -> SageOutputPaths:
    """Get the global SAGE output paths instance."""
    return SageOutputPaths(project_root)


# Convenience functions for backward compatibility
def get_logs_dir(project_root: Optional[Union[str, Path]] = None) -> Path:
    """Get the logs directory."""
    return get_sage_paths(project_root).logs_dir


def get_output_dir(project_root: Optional[Union[str, Path]] = None) -> Path:
    """Get the output directory."""
    return get_sage_paths(project_root).output_dir


def get_temp_dir(project_root: Optional[Union[str, Path]] = None) -> Path:
    """Get the temp directory."""
    return get_sage_paths(project_root).temp_dir


def get_log_file(name: str, subdir: Optional[str] = None, 
                 project_root: Optional[Union[str, Path]] = None) -> Path:
    """Get a log file path."""
    return get_sage_paths(project_root).get_log_file(name, subdir)


def get_output_file(name: str, subdir: Optional[str] = None,
                    project_root: Optional[Union[str, Path]] = None) -> Path:
    """Get an output file path."""
    return get_sage_paths(project_root).get_output_file(name, subdir)


def migrate_existing_outputs(project_root: Optional[Union[str, Path]] = None):
    """Migrate existing outputs to .sage directory."""
    get_sage_paths(project_root).migrate_existing_outputs()