"""
SAGE 维护工具模块

提供各种项目维护相关的工具：
- Dev-notes 文档整理
- 元数据修复
- Ruff 规则更新
- 等等

Author: SAGE Team
Date: 2025-10-27
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sage.tools.dev.maintenance.devnotes_organizer import DevNotesOrganizer
    from sage.tools.dev.maintenance.metadata_fixer import MetadataFixer
    from sage.tools.dev.maintenance.ruff_updater import RuffIgnoreUpdater

__all__ = [
    "DevNotesOrganizer",
    "MetadataFixer",
    "RuffIgnoreUpdater",
]


def __getattr__(name: str):
    """延迟导入以提高启动速度"""
    if name == "DevNotesOrganizer":
        from sage.tools.dev.maintenance.devnotes_organizer import DevNotesOrganizer

        return DevNotesOrganizer
    elif name == "MetadataFixer":
        from sage.tools.dev.maintenance.metadata_fixer import MetadataFixer

        return MetadataFixer
    elif name == "RuffIgnoreUpdater":
        from sage.tools.dev.maintenance.ruff_updater import RuffIgnoreUpdater

        return RuffIgnoreUpdater
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
