"""
SAGE Installation Modules
========================

Modular installation system for SAGE framework.
"""

from .base import Colors, BaseInstaller
from .system_manager import SystemManager
from .conda_manager import CondaManager
from .docker_manager import DockerManager
from .package_manager import PackageManager
from .menu_handler import MenuHandler
from .sage_installer import SageInstaller

__all__ = [
    'Colors',
    'BaseInstaller',
    'SystemManager',
    'CondaManager', 
    'DockerManager',
    'PackageManager',
    'MenuHandler',
    'SageInstaller'
]
