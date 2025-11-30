"""
SAGE Tools - Development and CLI Tools

Layer: L6 (Interface - CLI)
Dependencies: All layers (L1-L5)

提供开发和命令行工具:
- cli: 命令行接口
- dev: 开发工具
- finetune: 模型微调工具

Architecture:
- L6 界面层，提供命令行工具
- 依赖所有下层组件
- 用于命令行管理、开发和部署 SAGE 应用
"""

__layer__ = "L6"

from . import cli, dev
from ._version import __version__


# 延迟导入 finetune，避免在模块加载时就导入重量级依赖 (datasets, transformers, torch 等)
def __getattr__(name):
    """延迟导入 finetune 模块"""
    if name == "finetune":
        import importlib

        # Redirect to sage.libs.finetune (Moved to L3)
        finetune_module = importlib.import_module("sage.libs.finetune")
        return finetune_module

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "cli",
    "dev",
    "finetune",  # type: ignore[attr-defined]
]
