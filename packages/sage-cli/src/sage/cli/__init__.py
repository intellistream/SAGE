"""SAGE CLI - Command Line Interface (L5)

Layer: L5 (Interface Layer)

Unified command-line interface for SAGE platform operations:
- App management (run, stop, status)
- LLM service control (start, stop, status)
- Cluster management
- Development tools

Architecture Rules:
- ✅ Can import from: L1-L4 (all lower layers)
- ❌ Must NOT be imported by: other packages (top layer, no upward dependencies)
"""

from ._version import __version__

__layer__ = "L5"

__all__ = [
    "__version__",
]
