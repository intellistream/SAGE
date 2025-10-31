"""
SAGE Middleware - 中间件和领域算子层

Layer: L4 (Domain Components)
Dependencies: sage.libs (L3), sage.kernel (L3), sage.platform (L2), sage.common (L1)

提供：
- 领域算子：RAG operators, LLM operators, Tool operators
- 中间件组件：
  * sage_db: 数据库抽象
  * sage_mem: 内存管理和缓存
  * sage_refiner: 数据精炼工具
  * sage_flow: 工作流编排
  * sage_tsdb: 时序数据库

Architecture:
- L4 层提供领域特定的功能组件
- 依赖 L1-L3 的基础设施和核心引擎
- 为 L5 (应用层) 提供可复用的领域组件
- 包含各种中间件和高级算子实现

子模块：
- operators/: 领域算子（RAG, LLM, Tools等）
- components/: 中间件组件（DB, Memory, Refiner等）
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
__layer__ = "L4"

from . import components, operators

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "operators",
    "components",
]
