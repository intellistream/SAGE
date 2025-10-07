"""Python bindings and wrappers for SAGE-Flow live here.

This package is intended to house all Python-side modules for the component.
"""

import os
import sys
import warnings

# Try to import the C++ extension module
_sage_flow = None
try:
    from . import _sage_flow  # noqa: F401
except ImportError as e:
    # Get the directory where this __init__.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    # Search for .so files and add their directories to sys.path
    search_paths = [
        current_dir,
        os.path.join(parent_dir, 'build'),
    ]
    
    so_file_found = None
    for search_path in search_paths:
        if os.path.exists(search_path):
            for f in os.listdir(search_path):
                if f.startswith('_sage_flow') and f.endswith('.so'):
                    so_file_found = os.path.join(search_path, f)
                    # Add the directory to sys.path
                    if search_path not in sys.path:
                        sys.path.insert(0, search_path)
                    break
        if so_file_found:
            break
    
    # Try to import again after adding to sys.path
    if so_file_found:
        try:
            import _sage_flow as _sage_flow_module
            _sage_flow = _sage_flow_module
            # Also make it available as a relative import
            sys.modules[__name__ + '._sage_flow'] = _sage_flow_module
        except ImportError as e2:
            warnings.warn(
                f"Found .so file at {so_file_found} but failed to import: {e2}",
                ImportWarning
            )
    else:
        warnings.warn(
            f"_sage_flow native module not found. Please build the extension by running "
            f"'sage extensions install sage_flow' or executing the build.sh under "
            f"packages/sage-middleware/src/sage/middleware/components/sage_flow. "
            f"Searched in: {search_paths}",
            ImportWarning
        )
