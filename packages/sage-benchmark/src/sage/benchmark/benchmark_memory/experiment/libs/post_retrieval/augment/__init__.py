"""Augment Actions - 结果增强

包含两种增强操作:
- augment: 添加 persona/traits/summary 等上下文信息
- augment.reinforce: 更新检索到的记忆的强度（MemoryBank）
"""

from .base import AugmentAction
from .reinforce import ReinforceAction

__all__ = ["AugmentAction", "ReinforceAction"]
