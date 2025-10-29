"""Python bindings and wrappers for SAGE-Flow live here.

This package is intended to house all Python-side modules for the component.
"""

# Try to import the C++ extension module
# If this fails, sage_flow.py will handle the fallback logic
try:
    from . import _sage_flow  # noqa: F401  # type: ignore[import-not-found]

    __all__ = ["_sage_flow"]
except ImportError:
    # sage_flow.py will handle finding and importing the .so file
    __all__ = []
