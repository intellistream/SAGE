"""
SAGE Applications Framework

This module provides high-level application components, plugins, and libraries
for building SAGE-based applications.
"""

__version__ = "1.0.1"

# Core application components
try:
    from .lib import *
except ImportError:
    pass

try:
    from .plugins import *
except ImportError:
    pass

# Enterprise features (if available and licensed)
try:
    from .enterprise import *
except ImportError:
    # Enterprise features not available or not licensed
    pass

__all__ = [
    "__version__",
]
