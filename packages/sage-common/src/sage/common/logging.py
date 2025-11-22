"""
SAGE Common - Logging Utilities Convenience Module

Layer: L1 (Foundation)

This is a convenience re-export module for logging utilities.
The actual implementation is in sage.common.utils.logging

Usage:
    from sage.common.logging import CustomLogger, get_logger

    logger = get_logger(__name__)
    logger.info("Hello, SAGE!")
"""

from sage.common.utils.logging import CustomFormatter, CustomLogger, get_logger

__all__ = ["CustomLogger", "CustomFormatter", "get_logger"]
