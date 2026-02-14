"""
SageDB Middleware Service

⚠️  DEPRECATED: This module's imports are no longer available.

SageVDB has been migrated to an independent PyPI package (isage-vdb).
The old .python.* submodules have been removed.

Migration:
    pip install isage-vdb

    # Old import (deprecated):
    # from sage.middleware.components.sage_vdb.python.sage_db import SageDB

    # New import:
    from sagevdb import SageVDB

For backward compatibility, use:
    from sage.middleware.components.sage_vdb import SageVDB
"""

import warnings

warnings.warn(
    "sage.middleware.components.sage_vdb.service is deprecated. "
    "SageVDB has migrated to 'isage-vdb' (import: sagevdb). "
    "See module docstring for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = []  # No exports - module deprecated
