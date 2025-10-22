"""
SAGE Libs - 算法库和 Agents 框架

提供：
- Agents 框架：构建智能代理
- RAG 工具：document_loaders, text_splitters
- io_utils：Source, Sink, Batch
- 工具集：各类实用工具
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# 导出子模块
from . import agents, io_utils, rag, tools, utils

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "agents",
    "io_utils",
    "rag",
    "tools",
    "utils",
]
