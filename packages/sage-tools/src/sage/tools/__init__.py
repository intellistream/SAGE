"""
SAGE Tools - Development and CLI Tools

Layer: L6 (Interface - CLI)
Dependencies: All layers (L1-L5)

提供开发和命令行工具:
- cli: 命令行接口
- dev: 开发工具
- finetune: 模型微调工具
- management: 管理工具
- studio: Studio 相关工具
- utils: 工具函数

Architecture:
- L6 界面层，提供命令行工具
- 依赖所有下层组件
- 用于命令行管理、开发和部署 SAGE 应用
"""

from . import cli, dev, finetune, management, studio, utils
from ._version import __version__

__all__ = [
    "__version__",
    "cli",
    "dev",
    "finetune",
    "management",
    "studio",
    "utils",
]
