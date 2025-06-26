import ray
import logging
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING, Union
from ray.actor import ActorHandle
from sage.utils.custom_logger import CustomLogger
from sage.core.graph import SageGraph, GraphEdge, GraphNode
from sage.core.dag.local.dag_node import BaseDAGNode,OneShotDAGNode
from sage.core.dag.ray.ray_multi_node import RayMultiplexerDagNode
from sage.core.dag.local.multi_dag_node import MultiplexerDagNode


class MixedDAG:
    def __init__(self, graph: SageGraph):
        self.name:str = graph.name
        # self.graph:SageGraph = graph
        self.nodes: Dict[str, Union[ActorHandle, BaseDAGNode]] = {}
        self.nodes_metadata: Dict[str, Dict[str, Any]] = {}  # node_name -> platform
        self.connections: List[Tuple[str, int, str, int]] = []  # (upstream_node, out_channel, downstream_node, in_channel)
        self.session_folder = CustomLogger.get_default_session_folder()
        self.logger = CustomLogger(
            object_name=f"MixedDAG_{self.name}",
            log_level="DEBUG",
            console_output=True,
            file_output=True
        )
        self.node_dependencies: Dict[str, List[str]] = {}  # node_name -> [upstream_node_names]
        self.spout_nodes: List[str] = []
        self._compile_graph()
    
    # TODO: 做一个新的，维护自身输入缓冲区的local_dag_node
    def _compile_graph(self, graph:SageGraph):
        for node_name, graph_node in graph.nodes.items():
            node = self.create_node_instance(graph_node)
            # Add to RayDAG - use graph's get_upstream_nodes method
            upstream_nodes = graph.get_upstream_nodes(node_name)
            # TODO: 修改加入节点的方法
            self.add_node(
                name=node_name,
                executor=node,
                is_spout=(graph_node.type == "source"),
                upstream_nodes=upstream_nodes
            )
    
    def create_node_instance(self, graph_node:GraphNode) -> Union[
        RayMultiplexerDagNode, MultiplexerDagNode]:
        if graph_node.config["platform"] == "ray":
            node = RayMultiplexerDagNode.remote(
                name=graph_node.name,
                operator_class=graph_node.operator,
                operator_config=graph_node.config,
                is_spout=(graph_node.type == "source"), 
                session_folder = self.session_folder
            )
            return node
        else: # Local node
            operator_instance = graph_node.operator(graph_node.config)
            node = MultiplexerDagNode(
                graph_node.name,
                operator_instance,
                config=graph_node.config,
                is_spout=(graph_node.type == "source"), 
                session_folder=self.session_folder
            )
            return node

    def add_node(self, name: str, executor:Any, is_spout: bool = False, 
                     upstream_nodes: List[str] = None):
        """
        Add a Ray actor to the DAG.
        
        Args:
            name: Actor name/identifier
            actor: Ray actor handle
            is_spout: Whether this actor is a spout (source) node
            upstream_nodes: List of upstream node names this actor depends on
        """
        def get_platform(self) -> str:
            """检测执行模式"""
            if isinstance(self._operator, ray.actor.ActorHandle):
                return "ray"
            elif hasattr(self._operator, 'remote'):
                return "ray_function"
            else:
                return "local"
        
        self.nodes[name] = executor
        self.nodes_metadata[name] = {
            'is_spout': is_spout,
            'upstream_nodes': upstream_nodes or [], 
            "platform": get_platform(executor)
        }
        
        if is_spout:
            self.spout_nodes.append(name)
        
        if upstream_nodes:
            self.node_dependencies[name] = upstream_nodes
        
        self.logger.debug(f"Added node '{name}' of platform {get_platform(executor)}.")

