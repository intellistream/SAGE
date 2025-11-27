"""
Tool selection module.

Provides tool selector strategies for choosing relevant tools based on queries.
"""

from .base import BaseToolSelector, SelectorResources, ToolSelectorProtocol
from .dfsdt_selector import DFSDTSelector
from .embedding_selector import EmbeddingSelector
from .gorilla_selector import GorillaSelector, GorillaSelectorConfig
from .hybrid_selector import HybridSelector, HybridSelectorConfig
from .keyword_selector import KeywordSelector
from .registry import (
    SelectorRegistry,
    create_selector_from_config,
    get_selector,
    register_selector,
)
from .schemas import (
    CONFIG_TYPES,
    AdaptiveSelectorConfig,
    DFSDTSelectorConfig,
    EmbeddingSelectorConfig,
    KeywordSelectorConfig,
    SelectorConfig,
    ToolPrediction,
    ToolSelectionQuery,
    TwoStageSelectorConfig,
    create_selector_config,
)
from .schemas import (
    GorillaSelectorConfig as GorillaSelectorConfigSchema,
)

# Auto-register built-in selectors
register_selector("keyword", KeywordSelector)
register_selector("embedding", EmbeddingSelector)
register_selector("hybrid", HybridSelector)
register_selector("gorilla", GorillaSelector)
register_selector("dfsdt", DFSDTSelector)

__all__ = [
    # Base classes
    "BaseToolSelector",
    "SelectorResources",
    "ToolSelectorProtocol",
    # Selector implementations
    "KeywordSelector",
    "EmbeddingSelector",
    "HybridSelector",
    "HybridSelectorConfig",
    "GorillaSelector",
    "GorillaSelectorConfig",
    "DFSDTSelector",
    "DFSDTSelectorConfig",
    # Registry
    "SelectorRegistry",
    "register_selector",
    "get_selector",
    "create_selector_from_config",
    # Schemas
    "SelectorConfig",
    "KeywordSelectorConfig",
    "EmbeddingSelectorConfig",
    "TwoStageSelectorConfig",
    "AdaptiveSelectorConfig",
    "ToolSelectionQuery",
    "ToolPrediction",
    "CONFIG_TYPES",
    "create_selector_config",
]
