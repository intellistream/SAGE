from typing import Dict, List, Any, Tuple, Union, TYPE_CHECKING
from ray.actor import ActorHandle

from draft.local_thread_pool import LocalThreadPool
from sage_jobmanager.runtime_context import RuntimeContext
from sage_runtime.dagnode.local_dag_node import LocalDAGNode
from sage_runtime.dagnode.base_dag_node import BaseDAGNode
from sage_runtime.task.base_task import BaseTask
from sage_runtime.router.connection import Connection
from sage_utils.custom_logger import CustomLogger
from sage_runtime.compiler import Compiler, GraphNode

if TYPE_CHECKING:
    from sage_core.api.env import BaseEnvironment 

# 这个dispatcher可以直接打包传给ray sage daemon service
class Dispatcher():
    def __init__(self, graph: Compiler, env:'BaseEnvironment'):
        self.graph = graph
        self.name:str = graph.name
        self.logger = CustomLogger(
            filename=f"MixedDAG_{self.name}",
            env_name= env.name,
            console_output="WARNING",
            file_output="DEBUG",
            global_output = "DEBUG",
        )
        # self.nodes: Dict[str, Union[ActorHandle, LocalDAGNode]] = {}
        self.tasks: Dict[str, BaseTask] = {}
        self.logger.info(f"Dispatcher '{self.name}' construction complete")
    

        

    
    def submit(self, graph: Compiler, env:'BaseEnvironment'):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling mixed DAG for graph: {self.name}")
        
        # 第一步：创建所有节点实例
        for node_name, graph_node in graph.nodes.items():
            # node_instance = graph_node.create_dag_node()
            node_instance = graph_node.transformation.dag_node_factory.create_node(graph_node.name, graph_node.runtime_context)

            self.tasks[node_name] = node_instance

            self.logger.debug(f"Added node '{node_name}' of type '{node_instance.__class__.__name__}'")
        
        # 第二步：建立节点间的连接
        for node_name, graph_node in graph.nodes.items():
            self._setup_node_connections(node_name, graph_node)
        
        self.logger.info(f"Mixed DAG submission completed: {len(self.tasks)} nodes")




    def _setup_node_connections(self, node_name: str, graph_node: GraphNode):
        """
        为节点设置下游连接
        
        Args:
            node_name: 节点名称
            graph_node: 图节点对象
        """
        output_handle = self.tasks[node_name]
        
        for broadcast_index, parallel_edges in enumerate(graph_node.output_channels):
            for parallel_index, parallel_edge in enumerate(parallel_edges):
                target_name = parallel_edge.downstream_node.name
                target_input_index = parallel_edge.input_index
                target_handle = self.tasks[target_name]

                connection = Connection(
                    broadcast_index=broadcast_index,
                    parallel_index=parallel_index,
                    target_name=target_name,
                    target_input_buffer = target_handle.get_input_buffer(),
                    target_input_index = target_input_index
                )
                try:
                    output_handle.add_connection(connection)
                    self.logger.debug(f"Setup connection: {node_name} -> {target_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error setting up connection {node_name} -> {target_name}: {e}", exc_info=True)

    def stop(self):
        for node_name, node_instance in self.tasks.items():
            node_instance.stop()
            self.logger.debug(f"Stopped node: {node_name}")