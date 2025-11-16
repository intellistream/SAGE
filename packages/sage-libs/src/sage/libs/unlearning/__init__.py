"""Compatibility shim for deprecated import path ``sage.libs.unlearning``."""

from __future__ import annotations

import importlib
import sys
import warnings

_TARGET = "sage.libs.privacy.unlearning"
_module = importlib.import_module(_TARGET)

warnings.warn(
    "Importing from 'sage.libs.unlearning' is deprecated; use 'sage.libs.privacy.unlearning' instead.",
    DeprecationWarning,
    stacklevel=2,
)

globals().update(_module.__dict__)
__all__ = getattr(_module, "__all__", [])
__doc__ = _module.__doc__
__path__ = getattr(_module, "__path__", [])
__spec__ = getattr(_module, "__spec__", None)

sys.modules[__name__] = _module
