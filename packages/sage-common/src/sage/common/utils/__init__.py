"""SAGE - Streaming-Augmented Generative Execution

Layer: L1 (Foundation - Common Utilities)

This package provides common utilities used across all SAGE packages.
Includes logging, serialization, system utilities, and configuration helpers.

Architecture:
    This is a L1 foundation package providing utility functions.
    Must NOT contain business logic, only reusable helper functions.
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.common._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# Export document processing utilities
from sage.common.utils.document_processing import (
    SUPPORTED_MARKDOWN_SUFFIXES,
    Section,
    chunk_text,
    iter_markdown_files,
    parse_markdown_sections,
    sanitize_metadata_value,
    slugify,
    truncate_text,
)

# Export logging utilities
from sage.common.utils.logging import CustomFormatter, CustomLogger, get_logger

# Export results collector
from sage.common.utils.results_collector import ResultsCollector, get_collector

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "SUPPORTED_MARKDOWN_SUFFIXES",
    "Section",
    "chunk_text",
    "iter_markdown_files",
    "parse_markdown_sections",
    "sanitize_metadata_value",
    "slugify",
    "truncate_text",
    # Logging
    "CustomLogger",
    "CustomFormatter",
    "get_logger",
    # Results Collector
    "ResultsCollector",
    "get_collector",
]

# Export formatting utilities
from sage.common.utils.formatting import (
    format_count,
    format_duration,
    format_duration_verbose,
    format_percentage,
    format_size,
    format_size_compact,
    format_timestamp,
)

# Update __all__ with formatting utilities
__all__.extend(
    [
        "format_size",
        "format_size_compact",
        "format_duration",
        "format_duration_verbose",
        "format_timestamp",
        "format_percentage",
        "format_count",
    ]
)
