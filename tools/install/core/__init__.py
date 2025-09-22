
# 动态加载版本信息
def _get_version_info():
    """动态获取版本信息"""
    import sys
    from pathlib import Path
    import os
    
    current_path = Path(__file__).resolve()
    # Search upwards for _version.py
    version_file = None
    for parent in [current_path.parent] + list(current_path.parents):
        candidate = parent / "_version.py"
        if candidate.exists():
            version_file = candidate
            break
    
    if version_file and version_file.exists():
        version_globals = {}
        with open(version_file, 'r', encoding='utf-8') as f:
            exec(f.read(), version_globals)
        return version_globals.get('__version__', 'unknown')
    return 'unknown'

__version__ = _get_version_info()

"""SAGE安装系统核心模块"""

__author__ = "SAGE Development Team"

from .environment_manager import EnvironmentManager
from .package_installer import PackageInstaller
from .dependency_checker import DependencyChecker
from .submodule_manager import SubmoduleManager

__all__ = [
    "EnvironmentManager",
    "PackageInstaller", 
    "DependencyChecker",
    "SubmoduleManager"
]
