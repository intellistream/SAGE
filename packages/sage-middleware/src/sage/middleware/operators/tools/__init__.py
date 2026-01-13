"""
Tool Operators

This module contains domain-specific tool operators:
- Search tools (web search, document search)
- Data extraction tools

These operators inherit from base operator classes in sage.kernel.operators
and implement tool-specific business logic.

Note: Some tools require heavy dependencies (torch, transformers).
      They are loaded lazily and will raise ImportError if dependencies are missing.
"""

import warnings
from typing import TYPE_CHECKING

# Core tools (minimal dependencies)
from sage.middleware.operators.tools.arxiv_paper_searcher import _Searcher_Tool
from sage.middleware.operators.tools.arxiv_searcher import ArxivSearcher
from sage.middleware.operators.tools.nature_news_fetcher import Nature_News_Fetcher_Tool
from sage.middleware.operators.tools.searcher_tool import BochaSearchTool
from sage.middleware.operators.tools.url_text_extractor import URL_Text_Extractor_Tool

# Heavy tools (require torch/transformers) - lazy load
_HEAVY_TOOLS_LOADED = False
ImageCaptioner = None  # type: ignore
text_detector = None  # type: ignore


def _load_heavy_tools():
    """Load tools that require torch/transformers."""
    global _HEAVY_TOOLS_LOADED, ImageCaptioner, text_detector
    if _HEAVY_TOOLS_LOADED:
        return
    try:
        from sage.middleware.operators.tools.image_captioner import ImageCaptioner as _IC
        from sage.middleware.operators.tools.text_detector import text_detector as _TD

        ImageCaptioner = _IC
        text_detector = _TD
        _HEAVY_TOOLS_LOADED = True
    except ImportError as e:
        warnings.warn(
            f"Heavy tool operators not available: {e}\n"
            "Install with: pip install torch transformers",
            UserWarning,
            stacklevel=2,
        )


def __getattr__(name: str):
    """Lazy load heavy tools on access."""
    if name in ("ImageCaptioner", "text_detector"):
        _load_heavy_tools()
        if name == "ImageCaptioner":
            return ImageCaptioner
        if name == "text_detector":
            return text_detector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BochaSearchTool",
    "_Searcher_Tool",
    "ArxivSearcher",
    "Nature_News_Fetcher_Tool",
    "ImageCaptioner",
    "text_detector",
    "URL_Text_Extractor_Tool",
]
