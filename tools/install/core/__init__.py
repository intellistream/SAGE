"""SAGE安装系统核心模块"""

__version__ = "1.0.0"
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
