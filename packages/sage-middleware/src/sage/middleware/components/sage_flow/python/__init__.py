"""Python bindings and wrappers for SAGE-Flow live here.

This package is intended to house all Python-side modules for the component.
"""

import os
import sys
import warnings

# Debug: Print current module info
_DEBUG = os.environ.get('SAGE_DEBUG_IMPORT', '').lower() in ('1', 'true', 'yes')
if _DEBUG:
    print(f"[SAGE_FLOW __init__] Loading from: {__file__}")
    print(f"[SAGE_FLOW __init__] __name__ = {__name__}")
    print(f"[SAGE_FLOW __init__] sys.path = {sys.path[:3]}...")

# Try to import the C++ extension module
try:
    from . import _sage_flow  # noqa: F401
    if _DEBUG:
        print(f"[SAGE_FLOW __init__] Successfully imported _sage_flow via relative import")
except ImportError as e:
    if _DEBUG:
        print(f"[SAGE_FLOW __init__] Relative import failed: {e}")
    
    # Get the directory where this __init__.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    if _DEBUG:
        print(f"[SAGE_FLOW __init__] current_dir = {current_dir}")
        print(f"[SAGE_FLOW __init__] Listing files in current_dir:")
        try:
            for f in os.listdir(current_dir):
                print(f"  - {f}")
        except Exception as e:
            print(f"  Error listing: {e}")
    
    # Search for .so files and add their directories to sys.path
    search_paths = [
        current_dir,  # Source directory
        os.path.join(parent_dir, 'build'),  # Build directory
    ]
    
    # Also check if there's a version in site-packages
    try:
        import site
        for site_dir in site.getsitepackages():
            site_sage_flow = os.path.join(
                site_dir, 'sage', 'middleware', 'components', 'sage_flow', 'python'
            )
            if os.path.exists(site_sage_flow):
                search_paths.append(site_sage_flow)
    except Exception:
        pass  # site.getsitepackages() may not be available
    
    so_file_found = None
    for search_path in search_paths:
        if os.path.exists(search_path):
            try:
                for f in os.listdir(search_path):
                    if f.startswith('_sage_flow') and f.endswith('.so'):
                        so_file_found = os.path.join(search_path, f)
                        # Add the directory to sys.path
                        if search_path not in sys.path:
                            sys.path.insert(0, search_path)
                        break
            except (OSError, PermissionError):
                continue
        if so_file_found:
            break
    
    # Try to import again after adding to sys.path
    if so_file_found:
        if _DEBUG:
            print(f"[SAGE_FLOW __init__] Found .so file: {so_file_found}")
            print(f"[SAGE_FLOW __init__] Attempting to import...")
        try:
            import _sage_flow  # noqa: F401
            # Also make it available as a relative import
            sys.modules[__name__ + '._sage_flow'] = _sage_flow
            if _DEBUG:
                print(f"[SAGE_FLOW __init__] Successfully imported _sage_flow via absolute import")
                print(f"[SAGE_FLOW __init__] Registered in sys.modules as: {__name__ + '._sage_flow'}")
        except ImportError as e2:
            if _DEBUG:
                print(f"[SAGE_FLOW __init__] Failed to import even after adding to sys.path: {e2}")
            warnings.warn(
                f"Found .so file at {so_file_found} but failed to import: {e2}",
                ImportWarning
            )
            _sage_flow = None  # Ensure it's None on failure
    else:
        if _DEBUG:
            print(f"[SAGE_FLOW __init__] No .so file found in any search path")
        warnings.warn(
            f"_sage_flow native module not found. Please build the extension by running "
            f"'sage extensions install sage_flow' or executing the build.sh under "
            f"packages/sage-middleware/src/sage/middleware/components/sage_flow. "
            f"Searched in: {search_paths}",
            ImportWarning
        )
        _sage_flow = None  # Ensure it's None when not found

if _DEBUG:
    print(f"[SAGE_FLOW __init__] Final _sage_flow = {_sage_flow}")

# Export _sage_flow so it can be imported from this module
__all__ = ['_sage_flow']
