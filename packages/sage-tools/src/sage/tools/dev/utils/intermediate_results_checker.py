"""
中间结果放置检查工具

此模块提供统一的API来检查项目中间结果文件和目录的放置情况，
确保所有中间结果都放置在 .sage/ 目录下，保持项目根目录整洁。

迁移到 sage-dev-tools，此处为兼容性 wrapper。
"""

try:
    from sage_dev_tools.quality import IntermediateResultsChecker

    __all__ = ["IntermediateResultsChecker"]
except ImportError as e:
    import warnings

    warnings.warn(
        f"sage-dev-tools not installed: {e}\nPlease install it: pip install isage-dev-tools",
        ImportWarning,
        stacklevel=2,
    )

    # Provide stub class for backward compatibility
    class IntermediateResultsChecker:  # type: ignore[no-redef]
        """Stub class - requires sage-dev-tools installation."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "IntermediateResultsChecker has been moved to sage-dev-tools.\n"
                "Install with: pip install isage-dev-tools"
            )

    __all__ = ["IntermediateResultsChecker"]
