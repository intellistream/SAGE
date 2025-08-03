"""
ExecutionGraph - 执行图模块

此文件保持向后兼容，导入新的模块化结构
推荐直接从 sage.jobmanager.execution_graph 包导入所需类
"""

# 向后兼容的导入
from .execution_graph import (
    GraphNode,
    ServiceNode, 
    GraphEdge,
    ExecutionGraph
)

__all__ = [
    'GraphNode',
    'ServiceNode',
    'GraphEdge', 
    'ExecutionGraph'
]
