"""
SAGE Extensions Package

This package contains C++ extensions for SAGE:
- sage_db: High-performance vector database
- sage_queue: Memory-mapped queue for inter-process communication  
- mmap_queue: Legacy queue (deprecated, use sage_queue)
"""

__version__ = "0.1.0"

# Optional extension manager (if available)
def get_extension_manager():
    """Get the extension manager for building and managing C++ extensions."""
    try:
        from .extension_manager import ExtensionManager
        return ExtensionManager()
    except ImportError:
        # Extension manager not available
        return None

# Expose common utilities
__all__ = ['get_extension_manager']
