
# 动态加载版本信息
def _get_version_info():
    """动态获取版本信息"""
    import sys
    from pathlib import Path
    
    current_path = Path(__file__).resolve()
    root_path = current_path.parent.parent
    version_file = root_path / "_version.py"
    
    if version_file.exists():
        version_globals = {}
        with open(version_file, 'r', encoding='utf-8') as f:
            exec(f.read(), version_globals)
        return version_globals.get('__version__', 'unknown')
    return 'unknown'

__version__ = _get_version_info()
\n"""SAGE安装系统核心模块"""


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
