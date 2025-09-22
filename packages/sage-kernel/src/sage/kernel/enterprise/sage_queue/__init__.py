"""
SAGE Memory-Mapped Queue Package

高性能进程间通信队列，基于mmap和C实现
支持与Python标准Queue兼容的接口，以及Ray Actor集成
"""

# Import from python submodule
try:
    from .python.sage_queue import SageQueue
    from .python.sage_queue_manager import SageQueueManager
    exported_classes = ['SageQueue', 'SageQueueManager']
except ImportError:
    # Graceful fallback if python module not available
    exported_classes = []

# Import C++ bindings if available
try:
    from . import sage_queue_bindings
    from .sage_queue_bindings import SimpleBoostQueue, RingBufferStats, RingBufferRef
    exported_classes.extend(['sage_queue_bindings', 'SimpleBoostQueue', 'RingBufferStats', 'RingBufferRef'])
except ImportError:
    # C++ extension not available
    sage_queue_bindings = None

__all__ = exported_classes
__version__ = "0.1.0"
__author__ = "SAGE Team"
