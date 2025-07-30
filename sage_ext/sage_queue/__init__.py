"""
SAGE Memory-Mapped Queue Package

高性能进程间通信队列，基于mmap和C实现
支持与Python标准Queue兼容的接口，以及Ray Actor集成
"""

# Import from python submodule
try:
    from .python.sage_queue import SageQueue
    from .python.sage_queue_manager import SageQueueManager
    __all__ = ['SageQueue', 'SageQueueManager']
except ImportError:
    # Graceful fallback if python module not available
    __all__ = []

__version__ = "0.1.0"
__author__ = "SAGE Team"
