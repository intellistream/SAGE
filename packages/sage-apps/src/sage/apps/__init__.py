"""
SAGE Apps Package

This is a compatibility package. The actual implementation has been moved to sage.libs.
For new code, please use sage.libs instead.

This package is kept for backward compatibility.
"""

import warnings

# Issue a deprecation warning when sage.apps is imported
warnings.warn(
    "sage.apps is deprecated and will be removed in a future version. "
    "Please use sage.libs instead.",
    DeprecationWarning,
    stacklevel=2
)

# For backward compatibility, you can optionally import everything from libs
# Uncomment the following lines if you want to provide access to libs content:
# from sage.libs import *
