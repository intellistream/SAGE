"""
Dev-notes 文档元数据批量修复工具

迁移到 sage-dev-tools，此处为兼容性 wrapper。

Author: SAGE Team
Date: 2025-10-27
"""

try:
    from sage_dev_tools.docs import MetadataFixer

    __all__ = ["MetadataFixer"]
except ImportError as e:
    import warnings

    warnings.warn(
        f"sage-dev-tools not installed: {e}\nPlease install it: pip install isage-dev-tools",
        ImportWarning,
        stacklevel=2,
    )

    # Provide stub class for backward compatibility
    class MetadataFixer:  # type: ignore[no-redef]
        """Stub class - requires sage-dev-tools installation."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "MetadataFixer has been moved to sage-dev-tools.\n"
                "Install with: pip install isage-dev-tools"
            )

    __all__ = ["MetadataFixer"]
