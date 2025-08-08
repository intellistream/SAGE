"""
SAGE Development Toolkit
========================

A unified development toolkit for the SAGE framework, providing integrated
tools for testing, dependency analysis, package management, and reporting.
"""

__version__ = "1.0.0"
__author__ = "IntelliStream Team"
__email__ = "intellistream@outlook.com"

# Delayed imports to avoid circular dependencies
def get_toolkit():
    """Get SAGEDevToolkit instance with lazy loading."""
    from .core.toolkit import SAGEDevToolkit
    return SAGEDevToolkit

def get_config():
    """Get ToolkitConfig class with lazy loading."""
    from .core.config import ToolkitConfig
    return ToolkitConfig
