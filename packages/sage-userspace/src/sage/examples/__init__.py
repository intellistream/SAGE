"""
SAGE Examples - 示例代码和教程

这个模块包含了 SAGE 框架的各种使用示例和教程。

Examples:
    >>> from sage.kernel.examples import tutorials
    >>> from sage.kernel.examples import rag
    >>> from sage.kernel.examples import agents
    >>> from sage.kernel.examples import streaming
    >>> from sage.kernel.examples import memory
    >>> from sage.kernel.examples import evaluation
    >>> from sage.kernel.examples import resources
"""

# 导入所有子模块
from . import tutorials
from . import rag  
from . import agents
from . import streaming
from . import memory
from . import evaluation
from . import resources

__all__ = [
    "tutorials",
    "rag", 
    "agents",
    "streaming",
    "memory",
    "evaluation",
    "resources"
]

__version__ = "1.0.0"

__version__ = "1.0.0"
__author__ = "IntelliStream Team"
__email__ = "intellistream@outlook.com"

# 导入主要示例模块
from . import tutorials
from . import rag
from . import agents
from . import streaming
from . import memory
from . import evaluation

__all__ = [
    "tutorials",
    "rag", 
    "agents",
    "streaming",
    "memory",
    "evaluation"
]

def list_examples():
    """列出所有可用的示例"""
    examples = {
        "tutorials": "基础教程和入门示例",
        "rag": "RAG (检索增强生成) 示例",
        "agents": "多智能体系统示例", 
        "streaming": "流处理示例",
        "memory": "内存管理示例",
        "evaluation": "评估和基准测试示例"
    }
    
    print("🎯 可用的 SAGE 示例:")
    for category, description in examples.items():
        print(f"  • {category}: {description}")
    
    print("\n📖 使用方法:")
    print("  from sage.kernel.examples import <category>")
    print("  # 查看具体示例: help(<category>)")

def get_example_path():
    """获取示例文件的路径"""
    import os
    return os.path.dirname(__file__)
