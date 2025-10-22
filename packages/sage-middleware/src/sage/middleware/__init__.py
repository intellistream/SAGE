"""
SAGE Middleware - 中间件和领域算子层

提供：
- 领域算子：RAG, LLM, Tools
- 中间件组件：sage_db, sage_mem, sage_refiner, sage_flow, sage_tsdb
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.middleware._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# 导出子模块
from . import components, operators

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "operators",
    "components",
]
