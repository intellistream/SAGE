"""
SAGE - Streaming-Augmented Generative Execution

This is the meta-package that aggregates all SAGE components:
- sage.common: Common utilities
- sage.kernel: Core kernel functionality
- sage.middleware: Middleware components
- sage.libs: Application libraries
- sage.tools: Development tools
"""

# Load version from _version.py
from sage._version import __author__, __email__, __version__

# Extend namespace package path to include all installed SAGE subpackages
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
]
