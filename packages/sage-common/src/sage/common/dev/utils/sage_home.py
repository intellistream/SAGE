"""
SAGE Home Directory Management

This module provides utilities for managing the SAGE home directory (~/.sage)
where all temporary files, logs, and reports are stored.
"""

import os
from pathlib import Path
from typing import Optional


def get_sage_home_dir() -> Path:
    """Get the SAGE home directory (~/.sage), creating it if necessary."""
    home_dir = Path.home() / '.sage'
    home_dir.mkdir(exist_ok=True)
    return home_dir


def get_project_sage_dir(project_name: str = "SAGE") -> Path:
    """Get the project-specific SAGE directory, creating it if necessary."""
    project_dir = get_sage_home_dir() / "projects" / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    subdirs = ['logs', 'reports', 'cache', 'temp', 'coverage']
    for subdir in subdirs:
        (project_dir / subdir).mkdir(exist_ok=True)
    
    return project_dir


def _get_sage_dir_for_project(project_name: str = "SAGE") -> Path:
    """Get the appropriate SAGE directory for a project.
    
    For the main SAGE project, returns ~/.sage directly.
    For other projects, returns ~/.sage/projects/<project_name>.
    """
    if project_name and project_name.upper() == "SAGE":
        sage_dir = get_sage_home_dir()
    else:
        sage_dir = get_project_sage_dir(project_name)
    
    # Ensure subdirectories exist
    subdirs = ['logs', 'reports', 'cache', 'temp', 'coverage']
    for subdir in subdirs:
        (sage_dir / subdir).mkdir(exist_ok=True)
    
    return sage_dir


def get_logs_dir(project_name: str = "SAGE") -> Path:
    """Get the logs directory within project SAGE home."""
    return _get_sage_dir_for_project(project_name) / 'logs'


def get_reports_dir(project_name: str = "SAGE") -> Path:
    """Get the reports directory within project SAGE home."""
    return _get_sage_dir_for_project(project_name) / 'reports'


def get_cache_dir(project_name: str = "SAGE") -> Path:
    """Get the cache directory within project SAGE home."""
    return _get_sage_dir_for_project(project_name) / 'cache'


def get_temp_dir(project_name: str = "SAGE") -> Path:
    """Get the temporary files directory within project SAGE home."""
    return _get_sage_dir_for_project(project_name) / 'temp'


def get_coverage_dir(project_name: str = "SAGE") -> Path:
    """Get the coverage reports directory within project SAGE home."""
    return _get_sage_dir_for_project(project_name) / 'coverage'


def create_symlink_if_needed(project_root: Path, link_name: str, target_path: Path) -> bool:
    """
    Create a symlink from project root to target path if it doesn't exist.
    
    Args:
        project_root: The project root directory
        link_name: Name of the symlink to create in project root (e.g., 'logs')
        target_path: Full path to link to
    
    Returns:
        True if symlink was created or already exists, False on error
    """
    try:
        link_path = project_root / link_name
        
        # If link already exists and points to correct target, we're done
        if link_path.is_symlink() and link_path.readlink() == target_path:
            return True
        
        # If something exists at link_path but it's not the right symlink, remove it
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_dir() and not link_path.is_symlink():
                # Move existing directory content to SAGE home if needed
                import shutil
                for item in link_path.iterdir():
                    target_item = target_path / item.name
                    if not target_item.exists():
                        shutil.move(str(item), str(target_item))
                link_path.rmdir()
            else:
                link_path.unlink()
        
        # Create the symlink
        link_path.symlink_to(target_path)
        return True
        
    except Exception as e:
        print(f"Warning: Could not create symlink {link_name} -> {target_path}: {e}")
        return False


def setup_project_symlinks(project_root: Path, project_name: str = None) -> dict:
    """
    Set up a single symlink from project root to SAGE home.
    
    For the main SAGE project, link directly to ~/.sage
    For other projects, link to ~/.sage/projects/<project_name>
    
    Returns:
        Dict with status of symlink creation
    """
    results = {}
    
    try:
        # Use the helper function to get the correct SAGE directory
        sage_home = _get_sage_dir_for_project(project_name)
        
        link_path = project_root / '.sage'
        
        # If link already exists and points to correct target, we're done
        if link_path.is_symlink() and link_path.readlink() == sage_home:
            results['.sage'] = True
            return results
        
        # If something exists at link_path but it's not the right symlink, remove it
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_dir() and not link_path.is_symlink():
                # Move existing directory content to SAGE home if needed
                import shutil
                for item in link_path.iterdir():
                    target_item = sage_home / item.name
                    if not target_item.exists():
                        shutil.move(str(item), str(target_item))
                link_path.rmdir()
            else:
                link_path.unlink()
        
        # Create the symlink
        link_path.symlink_to(sage_home)
        results['.sage'] = True
        
    except Exception as e:
        print(f"Warning: Could not create symlink .sage -> ~/.sage: {e}")
        results['.sage'] = False
    
    return results
