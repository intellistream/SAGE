"""
Ruff ignore 规则更新工具

批量更新所有 pyproject.toml 文件中的 ruff.lint.ignore 规则

迁移到 sage-dev-tools，此处为兼容性 wrapper。

Author: SAGE Team
Date: 2025-10-27
"""

try:
    from sage_dev_tools.quality import RuffIgnoreUpdater

    __all__ = ["RuffIgnoreUpdater"]
except ImportError as e:
    import warnings

    warnings.warn(
        f"sage-dev-tools not installed: {e}\nPlease install it: pip install isage-dev-tools",
        ImportWarning,
        stacklevel=2,
    )

    # Provide stub class for backward compatibility
    class RuffIgnoreUpdater:  # type: ignore[no-redef]
        """Stub class - requires sage-dev-tools installation."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "RuffIgnoreUpdater has been moved to sage-dev-tools.\n"
                "Install with: pip install isage-dev-tools"
            )

    __all__ = ["RuffIgnoreUpdater"]
