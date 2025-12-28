"""SAGE CLI - Command Line Interface (L6)

Layer: L6 (Interfaces)

Unified command-line interface for SAGE platform operations:
- App management (run, stop, status)
- LLM service control (start, stop, status)
- Gateway operations
- Cluster management
- Development tools

Architecture Rules:
- ✅ Can import from: L1-L5 (all lower layers)
- ❌ Must NOT be imported by: other packages (top layer, no upward dependencies)
"""

from ._version import __version__

__layer__ = "L6"

__all__ = [
    "__version__",
]
