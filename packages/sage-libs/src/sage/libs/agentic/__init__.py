"""agentic compatibility layer.

⚠️ DEPRECATION NOTICE:
agentic implementations have been externalized to isage-agentic.

Installation:
    pip install isage-agentic

Usage:
    # Use the interface layer
    from sage.libs.agentic.interface import create, register

    # Or import from external package
    from isage_agentic import *

Repository: https://github.com/intellistream/sage-agentic
PyPI: https://pypi.org/project/isage-agentic/
"""

import warnings

# Re-export interface
from .interface import *  # noqa: F401, F403

warnings.warn(
    "sage.libs.agentic implementations have been externalized. "
    "Install 'isage-agentic' for concrete implementations: "
    "pip install isage-agentic",
    DeprecationWarning,
    stacklevel=2,
)
