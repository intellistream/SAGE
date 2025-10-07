"""Python bindings and wrappers for SAGE-Flow live here.

This package is intended to house all Python-side modules for the component.
"""

# Try to import the C++ extension module
try:
    from . import _sage_flow  # noqa: F401
except ImportError as e:
    import warnings
    import os
    
    # Get the directory where this __init__.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    # Search for .so files
    so_files = []
    for root, dirs, files in os.walk(parent_dir):
        for f in files:
            if f.startswith('_sage_flow') and f.endswith('.so'):
                so_files.append(os.path.join(root, f))
    
    warnings.warn(
        f"_sage_flow native module not found. Please build the extension by running "
        f"'sage extensions install sage_flow' or executing the build.sh under "
        f"packages/sage-middleware/src/sage/middleware/components/sage_flow. "
        f"Searched in: {[current_dir, os.path.join(parent_dir, 'build')]}, "
        f"Found .so files: {bool(so_files)}",
        ImportWarning
    )
