"""
Git Hooks Management Module for SAGE Development.

This module provides tools to install, manage, and configure Git hooks
for code quality checks, architecture compliance, and dev-notes validation.
"""

from .installer import HooksInstaller
from .manager import HooksManager

__all__ = ["HooksInstaller", "HooksManager"]
