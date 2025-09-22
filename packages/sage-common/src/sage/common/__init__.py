"""
SAGE Common - Utilities, CLI & Development Tools

This package provides the core utilities, command-line interface, and development 
tools for the SAGE (Stream Analytics in Go-like Environments) framework.

Modules:
    utils: Core utilities for configuration, logging, and common helpers
    cli: Command-line interface and interactive tools  
    dev: Development toolkit for testing, quality control, and packaging
    frontend: Web interface and dashboard components
"""

__version__ = "0.1.0"
__author__ = "IntelliStream Team"
__email__ = "intellistream@outlook.com"

# Re-export commonly used functions and classes
from sage.common.utils.config import load_config
from sage.common.utils.logging import get_logger

__all__ = [
    "load_config",
    "get_logger",
]
