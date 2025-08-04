"""
SAGE Userspace Agents Basic - 基础智能代理

从 sage-lib.agents 模块迁移而来，提供基础智能代理功能：
- 问答代理
- 搜索代理  
- 分析代理
- 多代理协作

商业版 sage-userspace-agents-pro 提供企业级代理和高级AI策略。
"""

# 导入主要代理
try:
    from .agent import *
    from .answer_bot import *
    from .chief_bot import *
    from .critic_bot import *
    from .question_bot import *
    from .searcher_bot import *
except ImportError as e:
    import warnings
    warnings.warn(f"Some agents not available: {e}. Install with 'pip install sage-userspace[llm]'")

__all__ = [
    # 具体代理会通过各模块的 __all__ 导出
]
