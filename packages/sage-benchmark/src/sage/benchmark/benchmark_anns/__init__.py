"""
Benchmark ANNS - A streamlined benchmark for ANNS algorithms in congestion scenarios

This package provides a clean, minimal implementation for benchmarking ANNS algorithms
under congestion (streaming workload) scenarios.
"""

__version__ = "1.0.0"

from . import core
from . import algorithms
from . import datasets
from . import utils

__all__ = ['core', 'algorithms', 'datasets', 'utils']

