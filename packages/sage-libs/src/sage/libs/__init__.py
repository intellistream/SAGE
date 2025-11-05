"""
SAGE Libs - Generic Algorithm Library and Agent Framework

Layer: L3 (Core Libraries)
Dependencies: sage.kernel (L3), sage.platform (L2), sage.common (L1)

Provides:
- Agents: Generic agent framework (ReAct, Planning, etc.)
- IO: Unified input/output interfaces (Source, Sink, Batch)
- Workflow: Workflow optimization framework
- Unlearning: Machine unlearning algorithms
- Tools: Base tool infrastructure (BaseTool, ToolRegistry)
- Context: Context compression algorithms (LongRefiner, SimpleRefiner)

Note: Domain-specific components have been moved to sage.middleware (L4):
- RAG operators → sage.middleware.operators.rag
- Integrations (Milvus, Chroma, OpenAI, etc.) → sage.middleware.operators.rag.backends / llm.clients
- Filters (tool_filter, evaluate_filter) → sage.middleware.operators.filters
- Business context (ModelContext, SearchSession) → sage.middleware.context
- Domain tools (arxiv_searcher, image_captioner) → sage.middleware.operators.tools

Architecture:
- Same as sage-kernel at L3 layer, providing generic algorithms and frameworks
- sage-kernel: Focuses on streaming execution engine
- sage-libs: Focuses on generic algorithm library and high-level abstractions
- Independent and can be used separately

Module Structure:
- agents/: Generic agent framework patterns
- io/: Data source and sink abstractions
- workflow/: Workflow optimization framework
- tools/: Base tool classes (BaseTool, ToolRegistry)
- unlearning/: Machine unlearning algorithms
- context/: Context compression algorithms (moved from middleware/sage_refiner)
"""

# Load version information
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # Fallback to hardcoded version
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# Export submodules
__layer__ = "L3"

from . import (
    agents,
    context,
    io,
    tools,
    unlearning,
    workflow,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "agents",
    "context",
    "io",
    "tools",
    "unlearning",
    "workflow",
]
