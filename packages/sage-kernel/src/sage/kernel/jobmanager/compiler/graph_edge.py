"""
GraphEdge - 图边类

GraphEdge代表两个节点之间的连接，包含：
- 上游节点和下游节点的引用
- 输入索引（用于区分下游节点的不同输入通道）
- 队列描述符（现在不再使用，因为队列描述符在节点上）
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .graph_node import TaskNode
    from sage.kernel.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor


class GraphEdge:
    """
    图边类
    
    表示编译器图中两个节点之间的连接
    """
    
    def __init__(self, name: str, output_node: 'TaskNode', input_node: 'TaskNode' = None, input_index: int = 0):
        """
        初始化图边
        
        Args:
            name: 边的名称
            output_node: 上游节点（输出节点）
            input_node: 下游节点（输入节点）
            input_index: 输入索引，表示连接到下游节点的哪个输入通道
        """
        self.name: str = name
        self.upstream_node: 'TaskNode' = output_node
        self.downstream_node: 'TaskNode' = input_node
        self.input_index: int = input_index
        
        # 队列描述符已不再在边上维护，而是在下游节点上
        # 保留此字段是为了向后兼容，但实际不使用
        self.queue_descriptor: 'BaseQueueDescriptor' = None
    
    def __repr__(self) -> str:
        downstream_name = self.downstream_node.name if self.downstream_node else "None"
        return f"GraphEdge(name={self.name}, upstream={self.upstream_node.name}, downstream={downstream_name}, input_index={self.input_index})"
