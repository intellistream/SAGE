from typing import Dict, List, Any, Tuple, Union, TYPE_CHECKING
from ray.actor import ActorHandle

from sage_runtime.local_thread_pool import LocalThreadPool
from sage_runtime.runtime_context import RuntimeContext
from sage_runtime.dagnode.local_dag_node import LocalDAGNode
from sage_runtime.dagnode.ray_dag_node import RayDAGNode
from sage_runtime.dagnode.base_dag_node import BaseDAGNode
from sage_utils.local_tcp_server import LocalTcpServer
from sage_runtime.io.connection import Connection
from sage_utils.custom_logger import CustomLogger
from sage_runtime.compiler import Compiler, GraphNode

if TYPE_CHECKING:
    from sage_core.api.env import BaseEnvironment 


class MixedDAG():
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
        self.nodes: Dict[str, BaseDAGNode] = {}

        self.spout_nodes: Dict[str, BaseDAGNode] = {}

        self.connections: List[Connection] = []

        self.is_running: bool = False

        self._compile_graph(graph, env)
        # 启动 TCP 服务器
        self.logger.info(f"MixedDAG '{self.name}' construction complete")
    

        

    
    def _compile_graph(self, graph: Compiler, env:'BaseEnvironment'):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling mixed DAG for graph: {self.name}")
        
        # 第一步：创建所有节点实例
        for node_name, graph_node in graph.nodes.items():
            # node_instance = graph_node.create_dag_node()
            node_instance = graph_node.transformation.dag_node_factory.create_node(graph_node.name, graph_node.runtime_context)
            self.nodes[node_name] = node_instance
            if graph_node.is_spout:
                self.spout_nodes[node_name] = node_instance

            self.logger.debug(f"Added node '{node_name}' of type '{node_instance.__class__.__name__}'")
        
        # 第二步：建立节点间的连接
        for node_name, graph_node in graph.nodes.items():
            self._setup_node_connections(node_name, graph_node)
        
        self.logger.info(f"Mixed DAG compilation completed: {len(self.nodes)} nodes, "f"{len(self.spout_nodes)} spout nodes")




    def _setup_node_connections(self, node_name: str, graph_node: GraphNode):
        """
        为节点设置下游连接
        
        Args:
            node_name: 节点名称
            graph_node: 图节点对象
        """
        output_handle = self.nodes[node_name]
        
        for broadcast_index, parallel_edges in enumerate(graph_node.output_channels):
            for parallel_index, parallel_edge in enumerate(parallel_edges):
                target_name = parallel_edge.downstream_node.name
                target_input_index = parallel_edge.input_index
                target_handle = self.nodes[target_name]

                connection = Connection(
                    own_node=output_handle,
                    broadcast_index=broadcast_index,
                    parallel_index=parallel_index,
                    target_name=target_name,
                    target_node=target_handle,
                    target_input_index = target_input_index,
                )
                try:
                    if isinstance(output_handle, ActorHandle):
                        
                        output_handle.add_connection.remote(connection)
                        self.logger.debug(f"Setup Ray connection: {node_name} -> {target_name}")
                    else:
                        # 本地节点直接调用
                        output_handle.add_connection(connection)
                        self.logger.debug(f"Setup local connection: {node_name} -> {target_name}")
                        
                    # 记录连接信息
                    self.connections.append(connection)
                    
                except Exception as e:
                    self.logger.error(f"Error setting up connection {node_name} -> {target_name}: {e}", exc_info=True)

    def stop(self):
        if(not self.is_running):
            self.logger.warning(f"MixedDAG '{self.name}' is not running, nothing to stop")
            return
        
        for node_name, node_instance in self.spout_nodes.items():
            node_instance.stop()
            self.logger.debug(f"Stopped spout node: {node_name}")
        self.logger.info(f"Stopped all spout nodes in MixedDAG '{self.name}'")

    def close(self):
        """停止所有节点"""
        self.logger.info("Stopping all DAG nodes...")
        for node_name, node in self.nodes.items():
            try:
                node.stop()
                self.logger.debug(f"Stopped node: {node_name}")
                # Ray actors会在进程结束时自动清理
            except Exception as e:
                self.logger.error(f"Error stopping node {node_name}: {e}")
    
    def submit(self):
        self.logger.info(f"Submitting MixedDAG '{self.name}'")
        try:
            for node_name, node in self.nodes.items():
                if node.is_spout is False:
                    local_runtime = LocalThreadPool.get_instance()
                    local_runtime.submit_node(node)
        except Exception as e:
            self.logger.error(f"Failed to submit MixedDAG '{self.name}': {e}", exc_info=True)

    def execute_once(self, spout_node_name:str = None):
        self.logger.info(f"executing once")
        if(spout_node_name is None):
            for node_name, node_instance in self.nodes.items():
                # print(f"triggering spout node: {node_name}, is_spout:{node_instance.is_spout}")
                if(node_instance.is_spout):
                    node_instance.trigger()
                    self.logger.debug(f"triggering spout node: {node_name}")

        elif self.spout_nodes.get(spout_node_name, None) is not None:
            node = self.spout_nodes[spout_node_name]
            self.logger.debug(f"Running spout node: {node_name}")
            node.trigger()
        else:
            self.logger.warning(f"Spout node '{spout_node_name}' not found in MixedDAG '{self.name}'")

    def execute_streaming(self, spout_node_name:str = None):
        self.logger.info(f"executing streaming")
        self.is_running = True
        if(spout_node_name is None):
            for node_name, node_instance in self.spout_nodes.items():
                local_runtime = LocalThreadPool.get_instance()
                local_runtime.submit_node(node_instance)
                self.logger.debug(f"Running spout node: {node_name}")
        elif self.spout_nodes.get(spout_node_name, None) is not None:
            node_handle = self.nodes[spout_node_name]
            local_runtime = LocalThreadPool.get_instance()
            local_runtime.submit_node(node_handle)
            self.logger.debug(f"Running spout node: {node_name}")
        else:
            self.logger.warning(f"Spout node '{spout_node_name}' not found in MixedDAG '{self.name}'")


    def _handle_tcp_message(self, message: Dict[str, Any], client_address: tuple):
        """
        处理来自 Ray Actor 的 TCP 消息
        由于是 DAG 专用端口，所有消息都属于当前 DAG
        """
        try:
            message_type = message.get("type")
            
            if message_type == "ray_to_local":
                # Ray Actor 发送给本地节点的数据
                target_node_name = message["target_node"]
                data = message["data"]
                source_actor = message.get("source_actor", "unknown")
                
                # 查找目标节点（在当前 DAG 中）
                if target_node_name in self.nodes:
                    target_node = self.nodes[target_node_name]
                    
                    # 确保是本地节点
                    if isinstance(target_node, LocalDAGNode):
                        # 将数据放入目标节点的输入缓冲区
                        target_node.put(data)
                        
                        self.logger.debug(f"[DAG {self.name}] Delivered TCP message: {source_actor} -> "
                                        f"{target_node_name}")
                    else:
                        self.logger.warning(f"Target node '{target_node_name}' is not a local node")
                else:
                    self.logger.warning(f"Target node '{target_node_name}' not found in DAG '{self.name}'")
            else:
                self.logger.warning(f"Unknown TCP message type: {message_type} from {client_address}")
                
        except Exception as e:
            self.logger.error(f"Error processing TCP message from {client_address}: {e}", exc_info=True)


    def _detect_platform(self, executor: Any) -> str:
        """
        检测执行器的平台类型
        
        Args:
            executor: 执行器对象
            
        Returns:
            平台类型字符串
        """
        if isinstance(executor, ActorHandle):
            return "remote"
        elif hasattr(executor, 'remote'):
            return "ray_function" 
        elif isinstance(executor, LocalDAGNode):
            return "local"
        else:
            return "unknown"
