"""
Dev-notes 文档整理工具

帮助整理现有的 dev-notes 文档：
1. 分析文档内容
2. 建议分类目录
3. 检查元数据
4. 生成整理建议

迁移到 sage-dev-tools，此处为兼容性 wrapper。

Author: SAGE Team
Date: 2025-10-27
"""

try:
    from sage_dev_tools.docs import CATEGORY_KEYWORDS, DevNotesOrganizer

    __all__ = ["CATEGORY_KEYWORDS", "DevNotesOrganizer"]
except ImportError as e:
    import warnings

    warnings.warn(
        f"sage-dev-tools not installed: {e}\nPlease install it: pip install isage-dev-tools",
        ImportWarning,
        stacklevel=2,
    )

    # Provide stub class for backward compatibility
    class DevNotesOrganizer:  # type: ignore[no-redef]
        """Stub class - requires sage-dev-tools installation."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "DevNotesOrganizer has been moved to sage-dev-tools.\n"
                "Install with: pip install isage-dev-tools"
            )

    CATEGORY_KEYWORDS = {}  # type: ignore[misc]
    __all__ = ["CATEGORY_KEYWORDS", "DevNotesOrganizer"]
