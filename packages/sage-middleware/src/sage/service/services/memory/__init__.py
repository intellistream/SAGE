"""
Memory Service Module
记忆服务模块 - 包含记忆管理和编排服务
"""

# 新的编排服务
from .memory_orchestrator_service import MemoryOrchestratorService, create_memory_service_factory

# 兼容性导入
from .memory_service import MemoryService
from .memory_manager import MemoryManager

__all__ = [
    "MemoryOrchestratorService", 
    "create_memory_service_factory",
    "MemoryService",
    "MemoryManager"
]