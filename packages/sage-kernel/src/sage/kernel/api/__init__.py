"""
SAGE API模块

提供流处理的核心API接口
"""

from .datastream import DataStream
from .base_environment import BaseEnvironment

__all__ = ['DataStream', 'BaseEnvironment']