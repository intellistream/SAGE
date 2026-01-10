"""Agentic compatibility layer - Deprecated, use isage-agentic package.

⚠️ DEPRECATION NOTICE:
The agentic module has been externalized to the `isage-agentic` package.

Installation:
    pip install isage-agentic

Migration:
    # Old (deprecated)
    from sage.libs.agentic import agents, planning, workflow

    # New (recommended)
    from isage_agentic import agents, planning, workflow

The agentic implementations have been moved to:
    https://github.com/intellistream/sage-agentic

This compatibility layer will be removed in sage-libs v0.3.0.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "sage.libs.agentic is deprecated and will be removed in v0.3.0. "
    "Install 'isage-agentic' package instead: pip install isage-agentic. "
    "Then import from isage_agentic instead of sage.libs.agentic.",
    DeprecationWarning,
    stacklevel=2,
)

# Try to import from external package for backward compatibility
try:
    from isage_agentic import *  # noqa: F401, F403

    _EXTERNAL_AVAILABLE = True
    __all__ = [
        "agents",
        "planning",
        "workflow",
        "tool_selection",
        "sias",
        "reasoning",
        "evaluation",
    ]

except ImportError as e:
    _EXTERNAL_AVAILABLE = False
    _import_error = e

    def __getattr__(name):
        """Lazy error on attribute access."""
        raise ImportError(
            f"Cannot import '{name}' from sage.libs.agentic. "
            f"The agentic module has been externalized. "
            f"Please install: pip install isage-agentic. "
            f"Original error: {_import_error}"
        ) from _import_error

    __all__ = []

# Provide helpful error message if used incorrectly
if not _EXTERNAL_AVAILABLE:
    import sys

    print(
        "\n⚠️  WARNING: sage.libs.agentic has been externalized\n"
        "━" * 60 + "\n"
        "The agentic module is now a separate package.\n\n"
        "To fix this, run:\n"
        "    pip install isage-agentic\n\n"
        "Then update your imports:\n"
        "    from isage_agentic import agents, planning, workflow\n\n"
        "Repository: https://github.com/intellistream/sage-agentic\n"
        "━" * 60,
        file=sys.stderr,
    )
