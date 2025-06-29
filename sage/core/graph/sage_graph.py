from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, AnyStr, Dict, List, Set
from sage.api.env import StreamingExecutionEnvironment
from sage.api.transformation import BaseTransformation,TransformationType
from sage.utils.custom_logger import CustomLogger




class GraphNode:
    def __init__(self, name: str, transformation: BaseTransformation, parallel_index: int):
        self.name: str = name
        self.transformation: BaseTransformation = transformation
        self.parallel_index: int = parallel_index  # 在该transformation中的并行索引
        
        # 输入输出channels：每个channel是一个边的列表
        # input_channels[i] 对应第i个upstream transformation的所有并行连接
        # output_channels[i] 对应第i个downstream transformation的所有并行连接
        self.input_channels: List[List[GraphEdge]] = []
        self.output_channels: List[List[GraphEdge]] = []

class GraphEdge:
    def __init__(self,name:str,  upstream_node: GraphNode, upstream_channel: int, downstream_node:GraphNode = None, downstream_channel: int = None):
        """
        Initialize a graph edge with a source and target node.
        Args:
            source (str): The name of the source node.
            target (str): The name of the target node.
        """
        self.name: str = name
        self.upstream_node:GraphNode = upstream_node
        self.upstream_channel: int = upstream_channel
        self.downstream_node:GraphNode = downstream_node
        self.downstream_channel: int = downstream_channel

class SageGraph:
    def __init__(self, env:StreamingExecutionEnvironment):
        self.env = env
        self.name = env.name
        self.nodes:Dict[str, GraphNode] = {}
        self.edges:Dict[str, GraphEdge] = {}
        # 构建数据流之间的连接映射

        self.logger = CustomLogger(
            object_name=f"SageGraph_{env.name}",
            log_level="DEBUG",
            console_output=True,
            file_output=True
        )
        # 构建基础图结构
        self._build_graph_from_pipeline(env)
        
        self.logger.info(f"Successfully converted and optimized pipeline '{env.name}' to graph with {len(self.nodes)} nodes and {len(self.edges)} edges")

    def _build_graph_from_pipeline(self, env: StreamingExecutionEnvironment):
        """
        根据transformation pipeline构建图，支持并行度和多对多连接
        分为三步：1) 生成并行节点 2) 生成物理边 3) 创建图结构
        """
        transformation_to_nodes = {}  # transformation -> list of node names
        
        # 第一步：为每个transformation生成并行节点
        self.logger.debug("Step 1: Generating parallel nodes for each transformation")
        for transformation in env.pipeline:
            node_names = []
            for i in range(transformation.parallelism):
                # 生成节点名，包含并行度索引
                if hasattr(transformation, 'function_class'):
                    base_name = transformation.function_class.__name__
                elif hasattr(transformation, 'op_class'):
                    base_name = transformation.op_class.__name__
                else:
                    base_name = "transformation"
                
                node_name = f"{base_name}_{id(transformation)}_{i}"
                node_names.append(node_name)
            
            transformation_to_nodes[transformation] = node_names
            self.logger.debug(f"Generated {len(node_names)} parallel nodes for {transformation.transformation_type}: {node_names}")
        
        # 第二步：计算逻辑边数量（用于日志）
        self.logger.debug("Step 2: Counting logical edges")
        logical_edge_count = 0
        physical_edge_count = 0
        for transformation in env.pipeline:
            for upstream_transformation in transformation.upstream:
                logical_edge_count += 1
                upstream_parallelism = len(transformation_to_nodes[upstream_transformation])
                downstream_parallelism = len(transformation_to_nodes[transformation])
                physical_edge_count += upstream_parallelism * downstream_parallelism
        
        self.logger.debug(f"Total logical edges: {logical_edge_count}, total physical edges: {physical_edge_count}")
        
        # 第三步：创建图结构
        self.logger.debug("Step 3: Creating graph structure")
        
        # 3.1 创建所有节点
        for transformation in env.pipeline:
            node_names = transformation_to_nodes[transformation]
            # 为该transformation创建所有并行节点
            for i, node_name in enumerate(node_names):
                try:
                    node = GraphNode(node_name, transformation, i)
                    
                    # 初始化输入输出channels
                    # 输入channels数量 = upstream transformations数量
                    for _ in range(len(transformation.upstream)):
                        node.input_channels.append([])
                    
                    # 输出channels数量 = downstream transformations数量  
                    for _ in range(len(transformation.downstream)):
                        node.output_channels.append([])
                    
                    self.nodes[node_name] = node
                    self.logger.debug(f"Created node: {node_name} (parallel index: {i})")
                    
                except Exception as e:
                    self.logger.error(f"Error creating node {node_name}: {e}")
                    raise
        
        # 3.2 为每条逻辑边创建物理边并连接节点
        edge_counter = 0
        for transformation in env.pipeline:
            downstream_nodes = transformation_to_nodes[transformation]
            
            for upstream_idx, upstream_transformation in enumerate(transformation.upstream):
                upstream_nodes = transformation_to_nodes[upstream_transformation]
                
                # 找到downstream_transformation在upstream_transformation.downstream中的位置
                downstream_idx = upstream_transformation.downstream.index(transformation)
                
                # 创建m*n条物理边
                for i, upstream_node_name in enumerate(upstream_nodes):
                    for j, downstream_node_name in enumerate(downstream_nodes):
                        # 创建边名
                        edge_name = f"edge_{edge_counter}_{upstream_node_name}_to_{downstream_node_name}"
                        edge_counter += 1
                        
                        # 获取节点对象
                        upstream_node = self.nodes[upstream_node_name]
                        downstream_node = self.nodes[downstream_node_name]
                        
                        # 创建边对象并连接
                        edge = GraphEdge(
                            name=edge_name,
                            upstream_node=upstream_node,
                            upstream_channel=downstream_idx,  # 在上游节点的第downstream_idx个输出channel
                            downstream_node=downstream_node,
                            downstream_channel=upstream_idx   # 在下游节点的第upstream_idx个输入channel
                        )
                        
                        # 将边添加到节点的channels中
                        upstream_node.output_channels[downstream_idx].append(edge)
                        downstream_node.input_channels[upstream_idx].append(edge)
                        
                        # 将边添加到图中
                        self.edges[edge_name] = edge
                
                self.logger.debug(f"Connected {len(upstream_nodes)}×{len(downstream_nodes)} physical edges "
                                f"between {upstream_transformation.transformation_type.value} -> "
                                f"{transformation.transformation_type.value}")
        
        self.logger.info(f"Graph construction completed: {len(self.nodes)} nodes, {len(self.edges)} edges")

