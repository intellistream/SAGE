"""
SAGE Libs - Algorithm Library and Agent Framework

Layer: L3 (Core Libraries)
Dependencies: sage.kernel (L3), sage.platform (L2), sage.common (L1)

Provides:
- Agents: Agent framework (ReAct, Planning, etc.)
- RAG: Retrieval-Augmented Generation tools (document loaders, text splitters, vector stores)
- IO: Unified input/output interfaces (Source, Sink, Batch)
- Workflow: Workflow optimization framework
- Unlearning: Machine unlearning algorithms
- Tools: Various utility tools and helper functions
- Context: Context management
- Integrations: Third-party service integrations (OpenAI, Milvus, ChromaDB, etc.)
- Filters: Data filtering and transformation utilities

Architecture:
- Same as sage-kernel at L3 layer, providing algorithms and frameworks
- sage-kernel: Focuses on streaming execution engine
- sage-libs: Focuses on algorithm library and high-level abstractions
- Independent and can be used separately

Module Structure:
- agents/: Agent framework and pre-built bots
- rag/: RAG toolchain
- io/: Data source and sink abstractions (renamed from io_utils)
- workflow/: Workflow optimization framework (renamed from workflow_optimizer)
- tools/: Tool functions and helper classes
- unlearning/: Machine unlearning algorithms
- context/: Context management
- integrations/: Third-party service integrations (migrated from utils)
- filters/: Data filters and transformers (migrated from utils)
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
    filters,
    integrations,
    io,
    rag,
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
    "filters",
    "integrations",
    "io",
    "rag",
    "tools",
    "unlearning",
    "workflow",
]
