"""SAGE Common - Foundation Layer (L1) Infrastructure and Shared Components

Layer: L1 (Foundation)

This package provides the foundational infrastructure for all SAGE packages.
It contains NO business logic, only core types, utilities, and shared components.

Module Structure:
- core: Core types, exceptions, constants, and data structures
- components: Reusable components (embedding, vLLM service wrappers)
- config: Configuration management (output paths, environment setup)
- model_registry: Model lifecycle management utilities
- utils: Common utilities (logging, serialization, system helpers)

Architecture Rules:
- ✅ Can be imported by: L2-L6 (all upper layers)
- ❌ Must NOT import from: sage.kernel, sage.middleware, sage.libs, sage.apps
- ✅ May import: Standard library, external dependencies
"""

from . import components, config, core, model_registry, utils
from ._version import __version__

__all__ = [
    "__version__",
    "components",
    "config",
    "core",
    "model_registry",
    "utils",
]
