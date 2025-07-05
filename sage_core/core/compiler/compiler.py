from __future__ import annotations
from typing import Dict, List
from sage_core.api.env import BaseEnvironment
from sage_core.core.operator.transformation import Transformation
from sage_utils.custom_logger import CustomLogger

class GraphNode:
    def __init__(self, name: str,env:BaseEnvironment, transformation: Transformation, parallel_index: int):
        self.name: str = name
        self.transformation: Transformation = transformation
        self.env: BaseEnvironment = env  # 所属的环境
        self.parallel_index: int = parallel_index  # 在该transformation中的并行索引
        
        # 输入输出channels：每个channel是一个边的列表
        self.input_channels: List[List[GraphEdge]] = []
        # 表示自己第i个input channel接受的所有上游并行节点的输入
        self.output_channels: List[List[List[GraphEdge]]] = []
        # 表示自己第i个output channel输出的所有“广播目标”，其中每一个目标可以是并行的一组下游节点

        for _ in range(len(transformation.upstreams)):
            self.input_channels.append([])
        for _ in range(len(transformation.downstreams)):
            self.output_channels.append([])


class GraphEdge:
    def __init__(self,name:str,  upstream_node: GraphNode, upstream_channel: int, downstream_node:GraphNode = None, downstream_channel: int = None):
        """
        Initialize a compiler edge with a source and target node.
        Args:
            source (str): The name of the source node.
            target (str): The name of the target node.
        """
        self.name: str = name
        self.upstream_node:GraphNode = upstream_node
        self.upstream_channel: int = upstream_channel
        self.downstream_node:GraphNode = downstream_node
        self.downstream_channel: int = downstream_channel

class Compiler:
    def __init__(self, env:BaseEnvironment):
        self.env = env
        self.name = env.name
        self.nodes:Dict[str, GraphNode] = {}
        self.edges:Dict[str, GraphEdge] = {}
        # 构建数据流之间的连接映射

        self.logger = CustomLogger(
            object_name=f"Compiler_{env.name}",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        # 构建基础图结构
        self._build_graph_from_pipeline(env)
        
        self.logger.info(f"Successfully converted and optimized pipeline '{env.name}' to compiler with {len(self.nodes)} nodes and {len(self.edges)} edges")

    def _build_graph_from_pipeline(self, env: BaseEnvironment):
        """
        根据transformation pipeline构建图, 支持并行度和多对多连接
        分为三步: 1) 生成并行节点 2) 生成物理边 3) 创建图结构
        """
        trans_to_parallel_node_names = {}  # transformation -> list of node names
        
        # 第一步：为每个transformation生成并行节点名字表，同时创建节点
        self.logger.debug("Step 1: Generating parallel nodes for each transformation")
        node_count = 0
        for transformation in env.pipeline:
            node_names = []
            for i in range(transformation.parallelism):
                try:
                    node_name = f"{transformation.function_class.__name__}_{node_count}"
                    node_count += 1
                    node_names.append(node_name)
                    self.nodes[node_name] = GraphNode(node_name, env,  transformation, i)
                    self.logger.debug(f"Created node: {node_name} (parallel index: {i})")
                except Exception as e:
                    self.logger.error(f"Error creating node {node_name}: {e}")
                    raise
            trans_to_parallel_node_names[transformation] = node_names
            self.logger.debug(f"Generated {len(node_names)} parallel nodes for {transformation.operator_class.__name__}: {node_names}")
        
        # 第二步：计算逻辑边数量（用于日志）
        self.logger.debug("Step 2: Counting logical edges")
        logical_edge_count = 0
        physical_edge_count = 0
        for transformation in env.pipeline:
            for upstream_transformation,upstream_channel in transformation.upstreams:
                logical_edge_count += 1
                upstream_parallelism = len(trans_to_parallel_node_names[upstream_transformation])
                downstream_parallelism = len(trans_to_parallel_node_names[transformation])
                physical_edge_count += upstream_parallelism * downstream_parallelism
        
        self.logger.debug(f"Total logical edges: {logical_edge_count}, total physical edges: {physical_edge_count}")
        
        # 第三步：为每条逻辑边创建物理边并连接节点
        self.logger.debug("Step 3: Creating compiler structure")

        for transformation in env.pipeline:
            downstream_nodes = trans_to_parallel_node_names[transformation]
            
            for downstream_input_channel, (upstream_trans, upstream_output_channel) in enumerate(transformation.upstreams):
                upstream_nodes = trans_to_parallel_node_names[upstream_trans]
                
                # 找到downstream_transformation在upstream_transformation.downstream中的位置
                # downstream_idx = upstream_trans.downstream.index(transformation)
                # 创建m*n条物理边
                for i, upstream_node_name in enumerate(upstream_nodes):
                    upstream_node = self.nodes[upstream_node_name]
                    output_group_edges = []
                    for j, downstream_node_name in enumerate(downstream_nodes):
                        # 创建边名
                        edge_name = f"({upstream_node_name}, {upstream_output_channel})->({downstream_node_name},{downstream_input_channel})"
                        
                        # 获取节点对象
                        downstream_node = self.nodes[downstream_node_name]
                        
                        # 创建边对象并连接
                        edge = GraphEdge(
                            name=edge_name,
                            upstream_node=upstream_node,
                            upstream_channel=upstream_output_channel,
                            downstream_node=downstream_node,
                            downstream_channel=downstream_input_channel
                        )
                        self.logger.debug(f"Creating edge: {edge_name} ")
                        # 将边添加到节点的channels中
                        #upstream_node.output_channels[upstream_output_channel].append(edge)
                        output_group_edges.append(edge)
                        downstream_node.input_channels[downstream_input_channel].append(edge)
                        
                        # 将边添加到图中
                        self.edges[edge_name] = edge
                    upstream_node.output_channels[upstream_output_channel].append(output_group_edges)



                self.logger.debug(f"Connected {len(upstream_nodes)}×{len(downstream_nodes)} physical edges "
                                f"between {upstream_trans.operator_class.__name__} -> "
                                f"{transformation.operator_class.__name__}")
        
        self.logger.info(f"Graph construction completed: {len(self.nodes)} nodes, {len(self.edges)} edges")

    def debug_print_graph(self):
        """
        调试方法：打印图中所有节点的详细信息，包括节点名字、对应的transformation.function以及上下游连接信息
        支持新的channel结构：input_channel包含来自上游并行节点的边，output_channel包含多组广播目标
        """
        lines = []
        lines.append("\n")
        lines.append("=" * 80)
        lines.append(f"Graph Debug Information for '{self.name}'")
        lines.append("=" * 80)
        
        if not self.nodes:
            lines.append("No nodes in the graph")
            self.logger.debug("\n".join(lines))
            return
        
        # 按transformation类型分组显示节点
        transformation_groups = {}
        for node in self.nodes.values():
            transformation_name = node.transformation.operator_class.__name__
            if transformation_name not in transformation_groups:
                transformation_groups[transformation_name] = []
            transformation_groups[transformation_name].append(node)
        
        for transformation_name, nodes in transformation_groups.items():
            lines.append(f"\n📊 Transformation: {transformation_name}")
            lines.append(f"   Type: {nodes[0].transformation.type.value}")
            lines.append(f"   Parallelism: {len(nodes)}")
            
            # 显示function信息
            sample_transformation = nodes[0].transformation
            if sample_transformation.is_instance:
                function_info = f"Instance of {sample_transformation.operator_class.__name__}"
            else:
                function_info = f"Class {sample_transformation.operator_class.__name__} (not instantiated)"
            lines.append(f"   Function: {function_info}")
            
            # 显示每个并行节点的详细信息
            for node in nodes:
                lines.append(f"\n   🔗 Node: {node.name} (parallel_index: {node.parallel_index})")
                
                # 显示输入连接信息
                if node.input_channels:
                    lines.append(f"      📥 Input Channels ({len(node.input_channels)} channels):")
                    for channel_idx, channel_edges in enumerate(node.input_channels):
                        if channel_edges:
                            # 统计来自不同上游节点的边
                            upstream_info = {}
                            for edge in channel_edges:
                                upstream_trans = edge.upstream_node.transformation.operator_class.__name__
                                if upstream_trans not in upstream_info:
                                    upstream_info[upstream_trans] = []
                                upstream_info[upstream_trans].append(edge.upstream_node.name)
                            
                            lines.append(f"         Channel {channel_idx}: {len(channel_edges)} edges")
                            for upstream_trans, upstream_nodes in upstream_info.items():
                                lines.append(f"           from {upstream_trans}: {upstream_nodes}")
                        else:
                            lines.append(f"         Channel {channel_idx}: No incoming edges")
                else:
                    lines.append(f"      📥 Input: No input channels (source node)")
                
                # 显示输出连接信息
                if node.output_channels:
                    lines.append(f"      📤 Output Channels ({len(node.output_channels)} channels):")
                    for channel_idx, broadcast_groups in enumerate(node.output_channels):
                        if broadcast_groups:
                            lines.append(f"         Channel {channel_idx}: {len(broadcast_groups)} broadcast groups")
                            for group_idx, group_edges in enumerate(broadcast_groups):
                                if group_edges:
                                    # 统计发送到不同下游节点的边
                                    downstream_info = {}
                                    for edge in group_edges:
                                        downstream_trans = edge.downstream_node.transformation.operator_class.__name__
                                        if downstream_trans not in downstream_info:
                                            downstream_info[downstream_trans] = []
                                        downstream_info[downstream_trans].append(edge.downstream_node.name)
                                    
                                    lines.append(f"           Group {group_idx}: {len(group_edges)} edges")
                                    for downstream_trans, downstream_nodes in downstream_info.items():
                                        lines.append(f"             to {downstream_trans}: {downstream_nodes}")
                        else:
                            lines.append(f"         Channel {channel_idx}: No outgoing edges")
                else:
                    lines.append(f"      📤 Output: No output channels (sink node)")
        
        # 显示图的统计信息
        lines.append(f"\n📈 Graph Statistics:")
        lines.append(f"   Total Nodes: {len(self.nodes)}")
        lines.append(f"   Total Edges: {len(self.edges)}")
        lines.append(f"   Transformations: {len(transformation_groups)}")
        
        # 显示连接拓扑（基于transformation级别）
        lines.append(f"\n🔄 Connection Topology:")
        transformation_connections = {}
        for transformation_name, nodes in transformation_groups.items():
            downstream_transformations = set()
            for node in nodes:
                for channel in node.output_channels:
                    for group in channel:
                        for edge in group:
                            downstream_transformations.add(edge.downstream_node.transformation.operator_class.__name__)
            transformation_connections[transformation_name] = list(downstream_transformations)
        
        for transformation_name, downstream_list in transformation_connections.items():
            if downstream_list:
                lines.append(f"   {transformation_name} -> {downstream_list}")
            else:
                lines.append(f"   {transformation_name} -> [SINK]")
        
        # 显示数据分发模式信息
        lines.append(f"\n📡 Data Distribution Patterns:")
        for transformation_name, nodes in transformation_groups.items():
            sample_node = nodes[0]
            if sample_node.output_channels:
                for channel_idx, broadcast_groups in enumerate(sample_node.output_channels):
                    if broadcast_groups:
                        distribution_type = "Round-robin/Key-by" if len(broadcast_groups) > 1 else "Broadcast"
                        lines.append(f"   {transformation_name} Channel {channel_idx}: {distribution_type} ({len(broadcast_groups)} groups)")
        
        lines.append("=" * 80)
        
        # 一次性输出所有调试信息
        self.logger.debug("\n".join(lines))