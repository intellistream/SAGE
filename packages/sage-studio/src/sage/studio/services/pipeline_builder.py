"""
Pipeline Builder - 将 Studio 可视化模型转换为 SAGE Pipeline

职责：
1. 解析 VisualPipeline 的节点和连接
2. 拓扑排序节点以确定执行顺序
3. 将每个节点映射到对应的 SAGE Operator
4. 使用 SAGE DataStream API 构建 Pipeline
5. 返回可执行的 Environment

不负责：
- 执行 Pipeline（由 SAGE Engine 完成）
- UI 交互逻辑
- 状态管理（由 SAGE Engine 完成）
"""

from typing import Any, Dict, List, Optional, Set
from collections import defaultdict, deque

from sage.kernel.api.base_environment import BaseEnvironment
from sage.kernel.api.local_environment import LocalEnvironment

from ..models import VisualPipeline, VisualNode, VisualConnection
from .node_registry import get_node_registry


class PipelineBuilder:
    """
    将 Studio 的可视化 Pipeline 转换为 SAGE 可执行 Pipeline
    
    Usage:
        builder = PipelineBuilder()
        env = builder.build(visual_pipeline)
        job = env.execute()
    """
    
    def __init__(self):
        # 使用全局节点注册表
        self.registry = get_node_registry()
    
    def build(self, pipeline: VisualPipeline) -> BaseEnvironment:
        """
        从 VisualPipeline 构建 SAGE Pipeline
        
        Args:
            pipeline: Studio 的可视化 Pipeline 模型
            
        Returns:
            配置好的 SAGE 执行环境
            
        Raises:
            ValueError: 如果 Pipeline 结构无效
        """
        # 1. 验证 Pipeline
        self._validate_pipeline(pipeline)
        
        # 2. 拓扑排序节点
        sorted_nodes = self._topological_sort(pipeline)
        
        # 3. 创建执行环境
        env = LocalEnvironment()
        
        # 4. 构建 DataStream Pipeline
        stream = None
        node_outputs = {}  # 记录每个节点的输出 stream
        
        for node in sorted_nodes:
            operator_class = self._get_operator_class(node.type)
            
            if stream is None:
                # 第一个节点 - 创建 source
                source_class, source_args, source_kwargs = self._create_source(node, pipeline)
                stream = env.from_source(source_class, *source_args, name=node.label, **source_kwargs)
            else:
                # 后续节点 - 添加 transformation
                stream = stream.map(
                    operator_class,
                    config=node.config,
                    name=node.label
                )
            
            node_outputs[node.id] = stream
        
        # 5. 添加 sink
        if stream:
            stream.sink(self._create_sink(pipeline))
        
        return env
    
    def _validate_pipeline(self, pipeline: VisualPipeline):
        """验证 Pipeline 结构的有效性"""
        if not pipeline.nodes:
            raise ValueError("Pipeline must contain at least one node")
        
        # 检查所有节点类型是否已注册
        for node in pipeline.nodes:
            if self.registry.get_operator(node.type) is None:
                raise ValueError(
                    f"Unknown node type: {node.type}. "
                    f"Available types: {self.registry.list_types()}"
                )
        
        # 检查连接是否有效
        node_ids = {node.id for node in pipeline.nodes}
        for conn in pipeline.connections:
            if conn.source_node_id not in node_ids:
                raise ValueError(f"Connection source not found: {conn.source_node_id}")
            if conn.target_node_id not in node_ids:
                raise ValueError(f"Connection target not found: {conn.target_node_id}")
    
    def _topological_sort(self, pipeline: VisualPipeline) -> List[VisualNode]:
        """
        对节点进行拓扑排序
        
        Returns:
            排序后的节点列表
            
        Raises:
            ValueError: 如果存在循环依赖
        """
        # 构建依赖图
        in_degree = defaultdict(int)
        adjacency = defaultdict(list)
        node_map = {node.id: node for node in pipeline.nodes}
        
        # 初始化入度
        for node in pipeline.nodes:
            in_degree[node.id] = 0
        
        # 构建图
        for conn in pipeline.connections:
            adjacency[conn.source_node_id].append(conn.target_node_id)
            in_degree[conn.target_node_id] += 1
        
        # Kahn 算法
        queue = deque([node_id for node_id in in_degree if in_degree[node_id] == 0])
        sorted_nodes = []
        
        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_map[node_id])
            
            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否存在循环
        if len(sorted_nodes) != len(pipeline.nodes):
            remaining = [n.label for n in pipeline.nodes if n not in sorted_nodes]
            raise ValueError(
                f"Circular dependency detected in pipeline. "
                f"Nodes in cycle: {remaining}"
            )
        
        return sorted_nodes
    
    def _get_operator_class(self, node_type: str):
        """获取节点类型对应的 Operator 类"""
        operator_class = self.registry.get_operator(node_type)
        if not operator_class:
            raise ValueError(f"Unknown node type: {node_type}. "
                           f"Available types: {self.registry.list_types()}")
        return operator_class
    
    def _create_source(self, node: VisualNode, pipeline: VisualPipeline):
        """
        创建数据源
        
        Returns:
            tuple: (source_class, args, kwargs)
        
        TODO: 根据节点类型和配置创建合适的 Source
        """
        from sage.kernel.api.function.source_function import SourceFunction
        
        # 简单实现：创建一个内存数据源类
        class SimpleListSource(SourceFunction):
            """Simple in-memory list source for testing"""
            def __init__(self, data):
                super().__init__()
                self.data = data
                self.index = 0
            
            def execute(self, context):
                """Execute the source function"""
                for item in self.data:
                    context.collect(item)
        
        initial_data = node.config.get("data", [{"input": "test"}])
        return SimpleListSource, (initial_data,), {}
    
    def _create_sink(self, pipeline: VisualPipeline):
        """
        创建数据接收器
        
        Returns:
            Type: Sink class (not instance)
        
        TODO: 根据 Pipeline 配置创建合适的 Sink
        """
        from sage.libs.io_utils.sink import PrintSink
        return PrintSink


# 全局 Builder 实例
_default_builder = None


def get_pipeline_builder() -> PipelineBuilder:
    """获取全局 PipelineBuilder 实例"""
    global _default_builder
    if _default_builder is None:
        _default_builder = PipelineBuilder()
    return _default_builder
