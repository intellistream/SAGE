"""SAGE Applications - Real-world AI applications built on SAGE framework.

This package contains production-ready applications demonstrating SAGE's
capabilities across various domains:

- video: Video intelligence and analysis
- medical_diagnosis: AI-assisted medical imaging diagnosis
"""

from . import medical_diagnosis, video
from ._version import __version__

__all__ = [
    "__version__",
    "medical_diagnosis",
    "video",
]
