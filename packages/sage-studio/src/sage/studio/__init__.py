"""
SAGE Studio - Web 界面管理工具

Layer: L6 (Interface - Web UI)
Dependencies: All layers (L1-L5)

提供 SAGE Studio 的 Web 界面管理功能。

主要组件:
- StudioManager: 主管理器
- models: 数据模型
- services: 服务层
- adapters: Pipeline 适配器（需要时手动导入）

Architecture:
- L6 界面层，提供可视化管理界面
- 依赖所有下层组件
- 用于可视化配置、监控和管理 SAGE 系统
"""

__layer__ = "L6"

from . import models, services
from ._version import __version__
from .chat_manager import ChatModeManager
from .studio_manager import StudioManager

__all__ = [
    "__version__",
    "StudioManager",
    "ChatModeManager",
    "models",
    "services",
]
