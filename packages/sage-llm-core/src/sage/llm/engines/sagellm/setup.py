# DEPRECATED: This file is kept for backward compatibility
# Please use pyproject.toml for modern Python packaging
# This file will be removed in a future version

import warnings

warnings.warn(
    "setup.py is deprecated. Please use pyproject.toml for packaging.",
    DeprecationWarning,
    stacklevel=2,
)

from setuptools import setup

setup()
