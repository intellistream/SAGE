"""
SAGE Memory-Mapped Queue Package

高性能进程间通信队列，基于mmap和C实现
支持与Python标准Queue兼容的接口，以及Ray Actor集成
"""

from .sage_queue import SageQueue, SageQueueRef,  destroy_queue

__version__ = "0.1.0"
__author__ = "SAGE Team"

__all__ = [
    'SageQueue',
    'SageQueueRef', 
    'create_queue',
    'open_queue',
    'destroy_queue'
]
