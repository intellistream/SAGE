from typing import Type, TYPE_CHECKING, Union, Any, AnyStr, Dict, List
from sage.api.operator import BaseOperator
from sage.core.engine import Engine
if TYPE_CHECKING:
    from sage.api.graph import GraphNode, GraphEdge, SageGraph




class GraphNode:
    def __init__(self,name:str, operator_class: Type[BaseOperator], type:str, operator_config: Dict = None):
        self.name: str = name
        self.type: str = type # "normal "or "source" or "sink"
        self.config: Dict = operator_config
        self.input_channels: list[GraphEdge] = []
        self.output_channels: list[GraphEdge] = []
        self.operator: Type[BaseOperator] = operator_class
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
    def __init__(self, name: str, config: dict = None):
        """
        Initialize the NodeGraph with a name and optional configuration.
        Args:
            name (str): The name of the node graph.
            config (dict, optional): Configuration parameters for the node graph.
        """
        self.name:str = name
        self.config:Dict = config or {}
        self.nodes:Dict[str, GraphNode] = {}
        self.edges:Dict[str, GraphEdge] = {}

    def add_node(self, 
                 node_name: str,
                 input_streams: Union[str, List[str]], 
                 output_streams: Union[str, List[str]], 
                 operator_class: Type[BaseOperator],
                 operator_config: Dict = None) -> GraphNode:
        """
        Add a node to the graph.
        Args:
            input_streams (Union[str, List[str]]): Input streams for the node.
            output_streams (Union[str, List[str]]): Output streams for the node.
            operator (Type[BaseOperator]): The operator class to be used by the node.
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
        
        # 根据输入输出流推断节点类型
        if not input_streams and output_streams:
            node_type = "source"
        elif input_streams and not output_streams:
            node_type = "sink"
        elif input_streams and output_streams:
            node_type = "normal"
        else:
            raise ValueError("Node must have at least input streams or output streams")
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
    
    def submit(self):
        engine:Engine = Engine.get_instance(generate_func=None)
        engine.submit_graph(self)
        print(f" Graph '{self.name}' submitted to engine.")
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
            if node.type == "sink" or not node.output_channels:
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
            print("Graph validation failed: No source nodes found")
            return False
        
        # Check if all edges are properly connected
        for edge_name, edge in self.edges.items():
            if edge.upstream_node is None:
                print(f"Graph validation failed: Edge '{edge_name}' has no upstream node")
                return False
            
            if edge.downstream_node is None:
                print(f"Graph validation failed: Edge '{edge_name}' has no downstream node")
                return False
        
        # Check for orphaned nodes (nodes with no connections)
        for node_name, node in self.nodes.items():
            if not node.input_channels and not node.output_channels:
                print(f"Graph validation failed: Node '{node_name}' is orphaned (no connections)")
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