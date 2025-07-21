import os
from typing import Dict, List, Any, Tuple, Union, TYPE_CHECKING
from sage_runtime.task.base_task import BaseTask
from sage_runtime.router.connection import Connection
from sage_utils.custom_logger import CustomLogger
from sage_jobmanager.execution_graph import ExecutionGraph, GraphNode
import ray
if TYPE_CHECKING:
    from sage_core.environment.base_environment import BaseEnvironment 

# 这个dispatcher可以直接打包传给ray sage daemon service
class Dispatcher():
    def __init__(self, graph: ExecutionGraph, env:'BaseEnvironment'):
        self.graph = graph
        self.env = env
        self.name:str = env.name
        self.logger = CustomLogger([
                ("console", "INFO"),  # 控制台显示重要信息
                (os.path.join(env.env_base_dir, "Dispatcher.log"), "DEBUG"),  # 详细日志
                (os.path.join(env.env_base_dir, "Error.log"), "ERROR")  # 错误日志
            ],
            name = f"Environment_{self.name}",
        )
        # self.nodes: Dict[str, Union[ActorHandle, LocalDAGNode]] = {}
        self.tasks: Dict[str, BaseTask] = {}
        self.logger.info(f"Dispatcher '{self.name}' construction complete")
        if env.platform is "remote" and not ray.is_initialized():
            ray.init(address="auto", _temp_dir="/var/lib/ray_shared")

    # Dispatcher will submit the job to LocalEngine or Ray Server.    
    def submit(self):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling Job for graph: {self.name}")
        
        # 第一步：创建所有节点实例
        for node_name, graph_node in self.graph.nodes.items():
            # task = graph_node.create_dag_node()
            task = graph_node.transformation.task_factory.create_task(graph_node.name, graph_node.runtime_context)

            self.tasks[node_name] = task

            self.logger.debug(f"Added node '{node_name}' of type '{task.__class__.__name__}'")
        
        # 第二步：建立节点间的连接
        for node_name, graph_node in self.graph.nodes.items():
            self._setup_node_connections(node_name, graph_node)
        
        # 第三步：提交所有节点开始运行
        for node_name, task in self.tasks.items():
            try:
                task.start_running()
                self.logger.debug(f"Started node: {node_name}")
            except Exception as e:
                self.logger.error(f"Failed to start node {node_name}: {e}", exc_info=True)
        self.logger.info(f"Job submission completed: {len(self.tasks)} nodes")


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