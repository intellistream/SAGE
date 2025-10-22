"""
SAGE Studio - Web 界面管理工具

提供 SAGE Studio 的 Web 界面管理功能。

主要组件:
- StudioManager: 主管理器
- models: 数据模型
- services: 服务层
- adapters: Pipeline 适配器（需要时手动导入）
"""

from . import models, services
from ._version import __version__
from .studio_manager import StudioManager

__all__ = [
    "__version__",
    "StudioManager",
    "models",
    "services",
]
