"""
Memory Service Module
记忆服务模块 - 提供统一的记忆管理和编排服务
"""

# 主要的记忆服务
from .memory_service import MemoryService, create_memory_service_factory

# 兼容性导入
from .memory_manager import MemoryManager

__all__ = [
    "MemoryService", 
    "create_memory_service_factory",
    "MemoryManager"
]