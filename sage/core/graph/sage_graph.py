from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, AnyStr, Dict, List, Set
from sage.api.pipeline.pipeline_api import Pipeline
from sage.api.pipeline.datastream_api import DataStream
from sage.api.operator import BaseFuction
from sage.utils.custom_logger import CustomLogger




class GraphNode:
    def __init__(self,name:str, operator_class: Type[BaseFuction], type:str, operator_config: Dict = None):
        self.name: str = name
        self.type: str = type # "normal "or "source" or "sink"
        self.config: Dict = operator_config
        self.input_channels: list[GraphEdge] = []
        self.output_channels: list[GraphEdge] = []
        self.operator: Type[BaseFuction] = operator_class
        pass

class GraphEdge:
    def __init__(self,name:str,  upstream_node: GraphNode, upstream_channel: int):
        """
        Initialize a graph edge with a source and target node.
        Args:
            source (str): The name of the source node.
            target (str): The name of the target node.
        """
        self.name: str = name
        self.upstream_node:GraphNode = upstream_node
        self.upstream_channel: int = upstream_channel
        self.downstream_node:GraphNode = None
        self.downstream_channnel: int = None

class SageGraph:
    def __init__(self, pipeline:Pipeline, config: dict = None, session_folder: str = None):
        """
        Initialize the NodeGraph with a name and optional configuration.
        Args:
            name (str): The name of the node graph.
            config (dict, optional): Configuration parameters for the node graph.
        """
        self.name:str = pipeline.name
        self.config:Dict = {
            "platform": "ray" if pipeline.use_ray else "local",
        }
        self.nodes:Dict[str, GraphNode] = {}
        self.edges:Dict[str, GraphEdge] = {}
        # 构建数据流之间的连接映射

        self.logger = CustomLogger(
            object_name=f"SageGraph_{self.name}",
            session_folder=session_folder,
            log_level="DEBUG",
            console_output=True,
            file_output=True
        )
        # 构建基础图结构
        self._build_graph_from_pipeline(pipeline)
        
        # 执行局部编译优化
        self._optimize_graph()
        
        # 验证优化后的图
        if not self.validate_graph():
            raise ValueError("Generated graph is invalid after optimization")
        
        self.logger.info(f"Successfully converted and optimized pipeline '{pipeline.name}' to graph with {len(self.nodes)} nodes and {len(self.edges)} edges")

    def _build_graph_from_pipeline(self, pipeline: Pipeline):
        stream_to_node_name = {}
        stream_connections = {}
        # 第一步：为每个 DataStream 生成唯一的节点名和边名
        for i, stream in enumerate(pipeline.data_streams):
            node_name = f"{stream.name}_{i}" if stream.name else f"node_{i}"
            stream_to_node_name[stream] = node_name
            
            # 构建连接映射：记录每个流的上下游边名
            input_edges = []
            output_edges = []
            
            # 处理输入边（来自上游流）
            for j, upstream in enumerate(stream.upstreams):
                edge_name = f"edge_{stream_to_node_name.get(upstream, f'upstream_{j}')}_{node_name}"
                input_edges.append(edge_name)
            
            # 处理输出边（到下游流）
            for j, downstream in enumerate(stream.downstreams):
                downstream_node_name = f"{downstream.name}_{pipeline.data_streams.index(downstream)}" if downstream.name else f"node_{pipeline.data_streams.index(downstream)}"
                edge_name = f"edge_{node_name}_{downstream_node_name}"
                output_edges.append(edge_name)
            
            stream_connections[stream] = {
                'node_name': node_name,
                'input_edges': input_edges,
                'output_edges': output_edges
            }


        # 第二步：按拓扑顺序添加节点到图中
        added_nodes = set()
        def add_node_recursively(stream: DataStream):
            """递归添加节点，确保上游节点先添加"""
            connection_info = stream_connections[stream]
            node_name = connection_info['node_name']
            
            # 如果节点已添加，跳过
            if node_name in added_nodes:
                return
            
            # 先添加所有上游节点
            for upstream in stream.upstreams:
                add_node_recursively(upstream)
            
            # 添加当前节点
            try:
                self.add_node(
                    node_name=node_name,
                    input_streams=connection_info['input_edges'],
                    output_streams=connection_info['output_edges'],
                    operator_class=stream.operator,
                    operator_config=stream.config, 
                    node_type=stream.node_type
                )
                added_nodes.add(node_name)
                self.logger.debug(f"Added node: {node_name}")
                
            except Exception as e:
                self.logger.debug(f"Error adding node {node_name}: {e}")
                raise
        
        # 从所有数据流开始添加（以处理可能的多个独立子图）
        for stream in pipeline.data_streams:
            add_node_recursively(stream)
    
    def _optimize_graph(self):
        """执行局部编译优化"""
        self.logger.info("Starting graph optimization...")
        
        # 记录优化前的状态
        initial_nodes = len(self.nodes)
        initial_edges = len(self.edges)
        
        # 1. 死代码消除：删除无效的非sink节点（没有有效输出路径的节点）
        self._eliminate_dead_code()
        
        # 2. 删除孤立节点（没有任何连接的节点）
        self._remove_orphaned_nodes()
        
        # 3. 简化冗余路径（可选，未来扩展）
        # self._simplify_redundant_paths()
        
        # 记录优化结果
        final_nodes = len(self.nodes)
        final_edges = len(self.edges)
        
        if initial_nodes != final_nodes or initial_edges != final_edges:
            self.logger.info(f"Graph optimization completed: "
                           f"nodes {initial_nodes} -> {final_nodes} "
                           f"(removed {initial_nodes - final_nodes}), "
                           f"edges {initial_edges} -> {final_edges} "
                           f"(removed {initial_edges - final_edges})")
        else:
            self.logger.debug("Graph optimization completed: no changes needed")

    def _eliminate_dead_code(self):
        """
        消除死代码：递归删除无法到达任何有效输出的节点
        类似编译器优化中的死变量消除
        """
        # 1. 标记所有有效的节点（能够到达sink节点或有外部输出的节点）
        valid_nodes = self._mark_reachable_nodes()
        
        # 2. 识别无效节点
        invalid_nodes = set(self.nodes.keys()) - valid_nodes
        
        if invalid_nodes:
            self.logger.info(f"Dead code elimination: removing {len(invalid_nodes)} unreachable nodes: {list(invalid_nodes)}")
            
            # 3. 递归删除无效节点
            for node_name in invalid_nodes:
                self._remove_node_and_edges(node_name)

    def _mark_reachable_nodes(self) -> Set[str]:
        """
        标记所有可达的有效节点
        从sink节点开始反向遍历，标记所有能到达有效输出的节点
        """
        valid_nodes = set()
        
        # 1. 获取所有sink节点作为初始有效节点
        sink_nodes = self.get_sink_nodes()
        if not sink_nodes:
            self.logger.warning("No sink nodes found, treating all leaf nodes as valid")
            # 如果没有明确的sink节点，将所有叶子节点视为有效
            sink_nodes = [name for name, node in self.nodes.items() 
                         if not node.output_channels]
        
        # 2. 从sink节点开始反向DFS标记
        def mark_upstream_recursive(node_name: str):
            if node_name in valid_nodes:
                return
            
            valid_nodes.add(node_name)
            self.logger.debug(f"Marked node '{node_name}' as reachable")
            
            # 递归标记所有上游节点
            for upstream_name in self.get_upstream_nodes(node_name):
                mark_upstream_recursive(upstream_name)
        
        # 标记所有从sink可达的节点
        for sink_name in sink_nodes:
            mark_upstream_recursive(sink_name)
        
        return valid_nodes

    def _remove_orphaned_nodes(self):
        """删除孤立节点（没有任何连接的节点）"""
        orphaned_nodes = []
        
        for node_name, node in self.nodes.items():
            if not node.input_channels and not node.output_channels:
                orphaned_nodes.append(node_name)
        
        if orphaned_nodes:
            self.logger.info(f"Removing {len(orphaned_nodes)} orphaned nodes: {orphaned_nodes}")
            for node_name in orphaned_nodes:
                self._remove_node_and_edges(node_name)

    def _remove_node_and_edges(self, node_name: str):
        """
        安全地删除节点及其相关的边
        """
        if node_name not in self.nodes:
            return
        
        node = self.nodes[node_name]
        
        # 删除与该节点相关的所有边
        edges_to_remove = []
        
        # 收集输入边
        for input_edge in node.input_channels:
            edges_to_remove.append(input_edge.name)
            # 断开上游节点的连接
            if input_edge.upstream_node:
                input_edge.upstream_node.output_channels = [
                    e for e in input_edge.upstream_node.output_channels 
                    if e.name != input_edge.name
                ]
        
        # 收集输出边
        for output_edge in node.output_channels:
            edges_to_remove.append(output_edge.name)
            # 断开下游节点的连接
            if output_edge.downstream_node:
                output_edge.downstream_node.input_channels = [
                    e for e in output_edge.downstream_node.input_channels 
                    if e.name != output_edge.name
                ]
        
        # 删除边
        for edge_name in edges_to_remove:
            if edge_name in self.edges:
                del self.edges[edge_name]
        
        # 删除节点
        del self.nodes[node_name]
        self.logger.debug(f"Removed node '{node_name}' and {len(edges_to_remove)} associated edges")

    def add_node(self, 
                 node_name: str,
                 input_streams: Union[str, List[str]], 
                 output_streams: Union[str, List[str]], 
                 operator_class: Type[BaseFuction],
                 operator_config: Dict = None, 
                 node_type: str = "normal") -> GraphNode:
        """
        Add a node to the graph.
        Args:
            input_streams (Union[str, List[str]]): Input streams for the node.
            output_streams (Union[str, List[str]]): Output streams for the node.
            operator (Type[BaseFuction]): The operator class to be used by the node.
        Returns:
            GraphNode: The created graph node.
        """
        # 标准化输入输出流为列表
        if isinstance(input_streams, str):
            input_streams = [input_streams] if input_streams else []
        elif input_streams is None:
            input_streams = []
        
        if isinstance(output_streams, str):
            output_streams = [output_streams] if output_streams else []
        elif output_streams is None:
            output_streams = []

        # 创建节点
        node = GraphNode(node_name, operator_class, node_type, operator_config)
        # 检查节点名是否已存在
        if node.name in self.nodes:
            raise ValueError(f"Node with name '{node.name}' already exists")
        
        # 处理输入边（必须是图中已存在的边）
        # i是从0开始编号的
        for i, stream_name in enumerate(input_streams):
            if stream_name not in self.edges:
                raise ValueError(f"Input stream '{stream_name}' does not exist in the graph")
            
            edge = self.edges[stream_name]
            if edge.downstream_node is not None:
                raise ValueError(f"Input stream '{stream_name}' is already connected to another node")
            
            # 连接边到当前节点
            edge.downstream_node = node
            edge.downstream_channnel = i
            node.input_channels.append(edge)

        # 处理输出边（创建新的空边）
        for i, stream_name in enumerate(output_streams):
            # 检查边名是否已存在
            if stream_name in self.edges:
                raise ValueError(f"Output stream name '{stream_name}' already exists")
            # 创建新的输出边
            edge = GraphEdge(name=stream_name, upstream_node=node, upstream_channel=i)
            self.edges[stream_name] = edge
            node.output_channels.append(edge)
        
        # 将节点添加到图中
        self.nodes[node.name] = node
        return node
    
    # def submit(self):
    #     engine:Engine = Engine.get_instance(generate_func=None)
    #     engine.submit_graph(self)
    #     self.logger.debug(f" Graph '{self.name}' submitted to engine.")
    def get_upstream_nodes(self, node_name: str) -> List[str]:
        """
        Get list of upstream node names for a given node.
        
        Args:
            node_name: Name of the node to find upstream nodes for
            
        Returns:
            List of upstream node names
        """
        if node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found in graph")
        
        graph_node = self.nodes[node_name]
        upstream_nodes = []
        
        for input_edge in graph_node.input_channels:
            if input_edge.upstream_node:
                upstream_nodes.append(input_edge.upstream_node.name)
        
        return upstream_nodes
    
    def get_downstream_nodes(self, node_name: str) -> List[str]:
        """
        Get list of downstream node names for a given node.
        
        Args:
            node_name: Name of the node to find downstream nodes for
            
        Returns:
            List of downstream node names
        """
        if node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found in graph")
        
        graph_node = self.nodes[node_name]
        downstream_nodes = []
        
        for output_edge in graph_node.output_channels:
            if output_edge.downstream_node:
                downstream_nodes.append(output_edge.downstream_node.name)
        
        return downstream_nodes
    
    def get_node_connections(self, node_name: str) -> Dict[str, List[str]]:
        """
        Get both upstream and downstream connections for a node.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Dictionary with 'upstream' and 'downstream' keys containing node name lists
        """
        return {
            'upstream': self.get_upstream_nodes(node_name),
            'downstream': self.get_downstream_nodes(node_name)
        }
    
    def get_source_nodes(self) -> List[str]:
        """
        Get all source nodes (nodes with no upstream connections).
        
        Returns:
            List of source node names
        """
        source_nodes = []
        for node_name, node in self.nodes.items():
            if node.type == "source" or not node.input_channels:
                source_nodes.append(node_name)
        return source_nodes
    
    def get_sink_nodes(self) -> List[str]:
        """
        Get all sink nodes (nodes with no downstream connections).
        
        Returns:
            List of sink node names
        """
        sink_nodes = []
        for node_name, node in self.nodes.items():
            self.logger.debug(f"Checking node '{node_name}' of type '{node.type}'")
            if node.type == "sink": # or not node.output_channels:
                sink_nodes.append(node_name)
        return sink_nodes
    
    def validate_graph(self) -> bool:
        """
        Validate the graph structure.
        
        Returns:
            True if graph is valid, False otherwise
        """
        # Check if graph has at least one source node
        if not self.get_source_nodes():
            self.logger.debug("Graph validation failed: No source nodes found")
            return False
        
        # Check if all edges are properly connected
        for edge_name, edge in self.edges.items():
            if edge.upstream_node is None:
                self.logger.debug(f"Graph validation failed: Edge '{edge_name}' has no upstream node")
                return False
            
            if edge.downstream_node is None:
                self.logger.debug(f"Graph validation failed: Edge '{edge_name}' has no downstream node")
                return False
        
        # Check for orphaned nodes (nodes with no connections)
        for node_name, node in self.nodes.items():
            if not node.input_channels and not node.output_channels:
                self.logger.debug(f"Graph validation failed: Node '{node_name}' is orphaned (no connections)")
                return False
        
        return True
    
    def get_graph_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the graph.
        
        Returns:
            Dictionary containing graph statistics and structure info
        """
        return {
            'name': self.name,
            'config': self.config,
            'node_count': len(self.nodes),
            'edge_count': len(self.edges),
            'source_nodes': self.get_source_nodes(),
            'sink_nodes': self.get_sink_nodes(),
            'nodes': list(self.nodes.keys()),
            'edges': list(self.edges.keys())
        }