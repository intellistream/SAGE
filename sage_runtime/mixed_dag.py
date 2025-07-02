from typing import Dict, List, Any, Tuple, Union
from ray.actor import ActorHandle

from sage_runtime import LocalRuntime, RayRuntime
from sage_runtime.local.local_dag_node import LocalDAGNode
from sage_runtime.ray.ray_dag_node import RayDAGNode
from sage_utils.custom_logger import CustomLogger
from sage.core.compiler import Compiler, GraphNode



class MixedDAG:
    def __init__(self, graph: Compiler, config):
        self.name:str = graph.name
        self.graph:Compiler = graph
        self.operators: Dict[str, Union[ActorHandle, LocalDAGNode]] = {}
        self.connections: List[Tuple[str, int, str, int]] = []  # (upstream_node, out_channel, downstream_node, in_channel)
        self.session_folder = CustomLogger.get_session_folder()
        self.ray_handles: List[Any] = []  # 存储Ray Actor句柄
        self.local_handles: List[Any] = []  # 存储本地节点句柄
        self.logger = CustomLogger(
            object_name=f"MixedDAG_{self.name}",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        self.node_dependencies: Dict[str, List[str]] = {}  # node_name -> [upstream_node_names]
        self.spout_nodes: List[str] = []
        self.is_running: bool = False
        self._compile_graph(config)
    
    def _compile_graph(self, config):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling mixed DAG for graph: {self.name}")
        
        # 第一步：创建所有节点实例
        for node_name, graph_node in self.graph.nodes.items():
            node_instance = self.create_node_instance(graph_node,config)
            # upstream_nodes = self.compiler.get_upstream_nodes(node_name)
            self.operators[node_name] = node_instance
            self.logger.debug(f"Added node '{node_name}' of type '{node_instance.__class__.__name__}'")
        
        # 第二步：建立节点间的连接
        for node_name, graph_node in self.graph.nodes.items():
            self._setup_node_connections(node_name, graph_node)
        
        self.logger.info(f"Mixed DAG compilation completed: {len(self.operators)} nodes, "f"{len(self.spout_nodes)} spout nodes")


    def _setup_node_connections(self, node_name: str, graph_node: GraphNode):
        """
        为节点设置下游连接
        
        Args:
            node_name: 节点名称
            graph_node: 图节点对象
        """
        current_operator = self.operators[node_name]
        
        # 为每个输出边添加下游连接
        for channel_index, output_edges in enumerate(graph_node.output_channels):
            for parallel_index, output_edge in enumerate(output_edges):
                downstream_node_name = output_edge.downstream_node.name
                downstream_operator = self.operators[downstream_node_name]
                
                try:
                    if isinstance(current_operator, ActorHandle):
                        # Ray节点调用远程方法
                        if(isinstance(downstream_operator, LocalDAGNode)):
                            downstream_handle = downstream_operator.name
                            # 利用本地节点名称，通过TCP连接发回数据
                        else:
                            downstream_handle = downstream_operator
                            # ActorHandle
                        
                        current_operator.add_downstream_node.remote(
                            output_edge.upstream_channel,
                            output_edge.downstream_channel,
                            downstream_handle
                        )
                        self.logger.debug(f"Setup Ray connection: {node_name} -> {downstream_node_name}")
                    else:
                        # 本地节点直接调用
                        current_operator.add_downstream_node(
                            output_edge.upstream_channel,
                            output_edge.downstream_channel,
                            downstream_operator
                        )
                        self.logger.debug(f"Setup local connection: {node_name} -> {downstream_node_name}")
                        
                    # 记录连接信息
                    self.connections.append((
                        node_name, 
                        output_edge.upstream_channel,
                        downstream_node_name, 
                        output_edge.downstream_channel
                    ))
                    
                except Exception as e:
                    self.logger.error(f"Error setting up connection {node_name} -> {downstream_node_name}: {e}")
                    raise        

    def create_node_instance(self, graph_node: GraphNode, config) -> Union[ActorHandle, LocalDAGNode]:
        """
        根据图节点创建对应的执行实例
        
        Args:
            graph_node: 图节点对象
            
        Returns:
            节点实例（Ray Actor或本地节点）
        """
        transformation = graph_node.transformation
        platform = graph_node.env.config.get("platform", "local")  # 默认使用本地平台
        col=graph_node.env.config.get("writer").get("ltm_collection")
        if platform == "remote":
            node = RayDAGNode.remote(
                name=graph_node.name,
                transformation=transformation,
                session_folder=self.session_folder,
                col=col
            )
            self.logger.debug(f"Created Ray actor node: {graph_node.name}")
            return node
        else:
            # 创建本地节点
            node = LocalDAGNode(
                name=graph_node.name,
                transformation=transformation,
                col=col
            )
            self.logger.debug(f"Created local node: {graph_node.name}")
            return node



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


    def start_all_nodes(self):
        """启动所有本地节点（Ray Actor会自动启动）"""
        self.logger.info("Starting all DAG nodes...")
        
        local_node_count = 0
        ray_node_count = 0
        
        for node_name, node_handle in self.operators.items():
            if isinstance(node_handle, LocalDAGNode):
                node = self.operators[node_name]
                node.start()
                local_node_count += 1
                self.logger.debug(f"Started local node: {node_name}")
            else:
                ray_node_count += 1
        
        self.logger.info(f"Started {local_node_count} local nodes, {ray_node_count} Ray actors")

    def stop_all_nodes(self):
        """停止所有节点"""
        self.logger.info("Stopping all DAG nodes...")
        
        for node_name, node_meta in self.operators.items():
            try:
                if isinstance(node_meta, ActorHandle) == False:
                    # local
                    node = self.operators[node_name]
                    node.stop()
                    self.logger.debug(f"Stopped local node: {node_name}")
                # Ray actors会在进程结束时自动清理
            except Exception as e:
                self.logger.error(f"Error stopping node {node_name}: {e}")
    
    def run(self) -> Dict[str, List[str]]:
        """
        启动MixedDAG执行，将所有节点注册到对应的运行时
        
        Returns:
            Dict: 包含各平台节点句柄的字典
        """
        if self.is_running:
            self.logger.warning(f"MixedDAG '{self.name}' is already running")
            return {"local_handles": self.local_handles, "ray_handles": self.ray_handles}
        
        self.logger.info(f"Starting MixedDAG '{self.name}' execution...")
        
        try:
            # 获取运行时实例

            
            local_runtime = LocalRuntime.get_instance()
            ray_runtime = RayRuntime.get_instance()
            
            # 分离本地节点和Ray节点
            local_nodes = []
            ray_actors = []
            ray_node_names = []
            
            for node_name, node_handle in self.operators.items():
                if isinstance(node_handle, LocalDAGNode):
                    local_node = self.operators[node_name]
                    local_nodes.append(local_node)
                elif isinstance(node_handle, ActorHandle):
                    ray_actor = self.operators[node_name]
                    ray_actors.append(ray_actor)
                    ray_node_names.append(node_name)
            
            # 提交本地节点到LocalRuntime
            if local_nodes:
                self.logger.info(f"Submitting {len(local_nodes)} local nodes to LocalRuntime")
                self.local_handles = local_runtime.submit_nodes(local_nodes)
                
                # 注册本地节点到TCP服务器（用于接收Ray Actor的数据）
                for local_node in local_nodes:
                    # 这里需要确保local_runtime知道节点名称映射
                    # 实际上submit_nodes已经在running_nodes中注册了
                    pass
                
                self.logger.info(f"Successfully submitted local nodes with handles: {self.local_handles}")
            
            # 提交Ray节点到RayRuntime
            if ray_actors:
                self.logger.info(f"Submitting {len(ray_actors)} Ray actors to RayRuntime")
                self.ray_handles = ray_runtime.submit_actors(ray_actors, ray_node_names)
                self.logger.info(f"Successfully submitted Ray actors with handles: {self.ray_handles}")
            
            # 启动所有节点
            # 在submit时所有节点就都启动了
            # self._start_all_nodes(local_runtime, ray_runtime)
            
            self.is_running = True
            self.logger.info(f"MixedDAG '{self.name}' started successfully with "
                           f"{len(self.local_handles)} local nodes and {len(self.ray_handles)} Ray actors")
            
            return {
                "local_handles": self.local_handles,
                "ray_handles": self.ray_handles,
                "total_nodes": len(self.local_handles) + len(self.ray_handles)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start MixedDAG '{self.name}': {e}", exc_info=True)
            # 清理已经提交的节点
            # self._cleanup_partial_submission(local_runtime, ray_runtime)
            raise