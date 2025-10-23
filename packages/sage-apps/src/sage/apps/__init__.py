"""SAGE Applications - Real-world AI applications built on SAGE framework.

Layer: L5 (Applications)
Dependencies: sage.middleware (L4), sage.libs (L3), sage.kernel (L3), sage.platform (L2), sage.common (L1)

This package contains production-ready applications demonstrating SAGE's
capabilities across various domains:

- video: Video intelligence and analysis
- medical_diagnosis: AI-assisted medical imaging diagnosis

Architecture:
- L5 应用层，组合使用下层功能构建完整应用
- 依赖 L4 领域组件和 L3 核心引擎
- 提供端到端的应用解决方案
"""

from . import medical_diagnosis, video
from ._version import __version__

__all__ = [
    "__version__",
    "medical_diagnosis",
    "video",
]
