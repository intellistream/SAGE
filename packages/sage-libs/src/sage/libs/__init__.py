"""
SAGE Libs - 算法库和 Agents 框架

Layer: L3 (Core Libraries)
Dependencies: sage.kernel (L3), sage.platform (L2), sage.common (L1)

提供：
- Agents 框架：构建智能代理系统
- RAG 工具：document_loaders, text_splitters, vector stores
- io_utils：Source, Sink, Batch 等 I/O 组件
- Unlearning：机器遗忘算法实现
- Tools：各类实用工具和辅助功能
- Applications：基于 agents 的应用示例

Architecture:
- 与 sage-kernel 同为 L3 层，提供算法和框架
- sage-kernel 专注流式执行引擎
- sage-libs 专注算法库和高级抽象
- 两者相互独立，可选依赖

模块说明：
- agents/: Agent 框架（ReAct, Planning等）
- rag/: RAG 工具链
- io_utils/: 数据源和汇聚工具
- tools/: 工具函数和辅助类
- unlearning/: 机器遗忘算法
- context/: 上下文管理
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
