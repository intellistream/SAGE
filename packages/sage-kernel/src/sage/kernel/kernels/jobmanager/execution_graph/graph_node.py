"""
GraphNode - 图节点类

每个GraphNode代表一个transformation的单个并行实例，包含：
- 单一输入队列描述符（被所有上游复用）
- 服务响应队列描述符
- 输入通道和输出通道的连接信息
- 运行时上下文
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from sage.api.base_environment import BaseEnvironment
    from sage.kernels.core.transformation.base_transformation import BaseTransformation
    from sage.kernels.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor
    from sage.kernels.runtime.task_context import TaskContext
    from .graph_edge import GraphEdge


class GraphNode:
    """
    图节点类
    
    每个GraphNode只有一个输入队列描述符 - 不是每个输入通道一个
    这个输入队列被所有上游节点复用 - 所有上游都写入同一个队列
    输入通道只是逻辑概念 - 用于区分不同的输入数据流，但物理上共享同一个队列
    """
    
    def __init__(self, name: str, transformation: 'BaseTransformation', parallel_index: int, env: 'BaseEnvironment'):
        self.name: str = name
        self.transformation: 'BaseTransformation' = transformation
        self.parallel_index: int = parallel_index  # 在该transformation中的并行索引
        self.parallelism: int = transformation.parallelism
        self.is_spout: bool = transformation.is_spout
        self.is_sink: bool = transformation.is_sink
        self.input_channels: Dict[int, List['GraphEdge']] = {}
        self.output_channels: List[List['GraphEdge']] = []
        
        # 在构造时创建队列描述符
        self._create_queue_descriptors(env)
        
        self.stop_signal_num: int = 0  # 预期的源节点数量
        self.ctx: 'TaskContext' = None
    
    def _create_queue_descriptors(self, env: 'BaseEnvironment'):
        """在节点构造时创建队列描述符"""
        # 为每个节点创建单一的输入队列描述符（被所有上游复用）
        if not self.is_spout:  # 源节点不需要输入队列
            self.input_qd = env.get_qd(
                name=f"input_{self.name}",
                maxsize=10000
            )
        else:
            self.input_qd = None
        
        # 为每个graph node创建service response queue descriptor
        self.service_response_qd = env.get_qd(
            name=f"service_response_{self.name}",
            maxsize=10000
        )
    
    def __repr__(self) -> str:
        return f"GraphNode(name={self.name}, parallel_index={self.parallel_index}, is_spout={self.is_spout}, is_sink={self.is_sink})"
