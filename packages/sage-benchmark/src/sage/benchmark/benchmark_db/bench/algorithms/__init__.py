"""
Algorithms Module for Benchmark ANNS

This module provides algorithm interfaces and implementations.
All algorithms are automatically discovered from subdirectories.
"""

from .base import BaseANN, BaseStreamingANN, DummyStreamingANN
from .registry import (
    ALGORITHMS,
    auto_register_algorithms,
    discover_algorithms,
    get_algorithm,
    register_algorithm,
)

# 尝试导入各种算法 wrapper（向后兼容 - 已弃用）
try:
    from .candy_wrapper import CANDYWrapper, get_candy_algorithm

    __all_wrappers = ["CANDYWrapper", "get_candy_algorithm"]
except ImportError:
    __all_wrappers = []

try:
    from .faiss_wrapper import FaissWrapper

    __all_wrappers.extend(["FaissWrapper"])
except ImportError:
    pass

try:
    from .diskann_wrapper import DiskANNWrapper

    __all_wrappers.extend(["DiskANNWrapper"])
except ImportError:
    pass

try:
    from .puck_wrapper import PuckWrapper

    __all_wrappers.extend(["PuckWrapper"])
except ImportError:
    pass

__all__ = [
    "BaseANN",
    "BaseStreamingANN",
    "DummyStreamingANN",
    "ALGORITHMS",
    "register_algorithm",
    "get_algorithm",
    "discover_algorithms",
    "auto_register_algorithms",
] + __all_wrappers
