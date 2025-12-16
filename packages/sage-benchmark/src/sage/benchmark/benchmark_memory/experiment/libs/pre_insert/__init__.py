"""PreInsert Action 模块

重构后的 PreInsert 算子，采用策略模式实现各种 Action。
"""

from .base import BasePreInsertAction, PreInsertInput, PreInsertOutput
from .operator import PreInsert
from .registry import PreInsertActionRegistry

__all__ = [
    "PreInsert",
    "BasePreInsertAction",
    "PreInsertInput",
    "PreInsertOutput",
    "PreInsertActionRegistry",
]
