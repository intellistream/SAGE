"""Agent components for SAGE middleware.

Provides agent runtime and planning capabilities.

Note: This module requires isage-agentic. Install with:
    pip install isage-middleware[libs] or pip install isage-agentic
"""

import warnings

try:
    from sage.middleware.operators.agent import runtime

    _HAS_AGENTIC = True
    __all__ = ["runtime"]
except ImportError as e:
    _HAS_AGENTIC = False
    runtime = None  # type: ignore
    __all__ = []
    warnings.warn(
        f"Agent runtime not available: {e}\nInstall with: pip install isage-agentic",
        UserWarning,
        stacklevel=2,
    )
