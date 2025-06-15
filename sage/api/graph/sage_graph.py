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