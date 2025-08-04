"""
SAGE Development Toolkit
========================

A unified development toolkit for the SAGE framework, providing integrated
tools for testing, dependency analysis, package management, and reporting.

Features:
- Intelligent test execution based on code changes
- Comprehensive dependency analysis with circular dependency detection
- Unified package management across the SAGE ecosystem
- Rich reporting with multiple output formats
- Interactive and batch operation modes
- Extensible plugin architecture

Usage:
    from sage_dev_toolkit import SAGEDevToolkit
    
    toolkit = SAGEDevToolkit()
    toolkit.run_tests(mode="diff")
    toolkit.analyze_dependencies()
    toolkit.generate_report()
"""

__version__ = "1.0.0"
__author__ = "IntelliStream Team"
__email__ = "sage@intellistream.cc"

from .core.toolkit import SAGEDevToolkit
from .core.config import ToolkitConfig
from .core.exceptions import (
    SAGEDevToolkitError,
    ConfigError,
    ToolError,
    AnalysisError,
)

__all__ = [
    "SAGEDevToolkit",
    "ToolkitConfig", 
    "SAGEDevToolkitError",
    "ConfigError",
    "ToolError",
    "AnalysisError",
]
