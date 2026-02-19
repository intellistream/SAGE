"""
SAGE 废弃文件检查器

检查项目中没有被其他文件引用的Python文件，帮助清理代码库。

迁移到 sage-dev-tools，此处为兼容性 wrapper。
"""

try:
    from sage_dev_tools.quality import (
        OrphanedFile,
        OrphanedFileDetector,
        analyze_orphaned_files,
        format_file_size,
    )

    __all__ = [
        "OrphanedFile",
        "OrphanedFileDetector",
        "analyze_orphaned_files",
        "format_file_size",
    ]
except ImportError as e:
    import warnings

    warnings.warn(
        f"sage-dev-tools not installed: {e}\nPlease install it: pip install isage-dev-tools",
        ImportWarning,
        stacklevel=2,
    )

    # Provide stub for backward compatibility
    from dataclasses import dataclass
    from pathlib import Path

    @dataclass
    class OrphanedFile:  # type: ignore[no-redef]
        """Stub class - requires sage-dev-tools installation."""

        path: Path
        relative_path: Path
        module_path: str
        size_bytes: int
        last_modified: float

    class OrphanedFileDetector:  # type: ignore[no-redef]
        """Stub class - requires sage-dev-tools installation."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "OrphanedFileDetector has been moved to sage-dev-tools.\n"
                "Install with: pip install isage-dev-tools"
            )

    def analyze_orphaned_files(*args, **kwargs):  # type: ignore[misc]
        """Stub function - requires sage-dev-tools installation."""
        raise ImportError(
            "analyze_orphaned_files has been moved to sage-dev-tools.\n"
            "Install with: pip install isage-dev-tools"
        )

    def format_file_size(*args, **kwargs):  # type: ignore[misc]
        """Stub function - requires sage-dev-tools installation."""
        raise ImportError(
            "format_file_size has been moved to sage-dev-tools.\n"
            "Install with: pip install isage-dev-tools"
        )

    __all__ = [
        "OrphanedFile",
        "OrphanedFileDetector",
        "analyze_orphaned_files",
        "format_file_size",
    ]
