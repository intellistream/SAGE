from typing import Dict, List, Any, Tuple, Union
from ray.actor import ActorHandle

from sage_runtime.runtimes.local_runtime import LocalRuntime
from sage_runtime.runtimes.ray_runtime import RayRuntime
from sage_runtime.executor.local_dag_node import LocalDAGNode
from sage_runtime.executor.ray_dag_node import RayDAGNode
from sage_utils.custom_logger import CustomLogger
from sage_core.core.compiler import Compiler, GraphNode

class MixedDAG:
    def __init__(self, graph: Compiler):
        self.name:str = graph.name
        self.graph:Compiler = graph
        self.env = graph.env
        self.name_to_DAGnode: Dict[str, Union[ActorHandle, LocalDAGNode]] = {}
        self.connections: List[Tuple[str, str, str, str]] = []  # (upstream_node, out_tag, downstream_node, input_tag)
        self.session_folder = CustomLogger.get_session_folder()
        self.ray_handles: List[Any] = []  # 存储Ray Actor句柄
        self.local_handles: List[Any] = []  # 存储本地节点句柄
        self.logger = CustomLogger(
            filename=f"MixedDAG_{self.name}",
            console_output="WARNING",
            file_output="WARNING",
            global_output = "WARNING",
        )
        self.node_dependencies: Dict[str, List[str]] = {}  # node_name -> [upstream_node_names]
        self.spout_nodes: List[str] = []
        self.is_running: bool = False

        self._compile_graph()
        self.debug_print_operators()
    
    def _compile_graph(self):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling mixed DAG for graph: {self.name}")
        
        # 第一步：创建所有节点实例
        for node_name, graph_node in self.graph.nodes.items():
            node_instance = self.create_node_instance(graph_node)
            # upstream_nodes = self.compiler.get_upstream_nodes(node_name)
            self.name_to_DAGnode[node_name] = node_instance
            self.logger.debug(f"Added node '{node_name}' of type '{node_instance.__class__.__name__}'")
        
        # 第二步：建立节点间的连接
        for node_name, graph_node in self.graph.nodes.items():
            self._setup_node_connections(node_name, graph_node)
        
        self.logger.info(f"Mixed DAG compilation completed: {len(self.name_to_DAGnode)} nodes, "f"{len(self.spout_nodes)} spout nodes")

    def _setup_node_connections(self, node_name: str, graph_node: GraphNode):
        """
        为节点设置下游连接
        
        Args:
            node_name: 节点名称
            graph_node: 图节点对象
        """
        current_dag_node = self.name_to_DAGnode[node_name]
        
        for output_tag, broadcasting_groups in graph_node.output_channels.items():
            for broadcast_index, parallel_edges in enumerate(broadcasting_groups):
                for parallel_index, parallel_edge in enumerate(parallel_edges):
                    downstream_node_name = parallel_edge.downstream_node.name
                    downstream_operator = self.name_to_DAGnode[downstream_node_name]
                    try:
                        if isinstance(current_dag_node, ActorHandle):
                            # Ray节点调用远程方法
                            if(isinstance(downstream_operator, LocalDAGNode)):
                                downstream_handle = downstream_operator.name
                                # 利用本地节点名称，通过TCP连接发回数据
                            else:
                                downstream_handle = downstream_operator
                                # ActorHandle
                            
                            current_dag_node.add_downstream_node.remote(
                                output_tag,
                                broadcast_index,
                                parallel_index,
                                parallel_edge.downstream_tag,
                                downstream_handle
                            )
                            self.logger.debug(f"Setup Ray connection: {node_name}[{output_tag}] -> {downstream_node_name}[{parallel_edge.downstream_tag}]")
                        else:
                            # 本地节点直接调用
                            current_dag_node.add_downstream_node(
                                output_tag,
                                broadcast_index,
                                parallel_index,
                                parallel_edge.downstream_tag,
                                downstream_operator
                            )
                            self.logger.debug(f"Setup local connection: {node_name}[{output_tag}] -> {downstream_node_name}[{parallel_edge.downstream_tag}]")
                            
                        # 记录连接信息
                        self.connections.append((
                            node_name, 
                            parallel_edge.upstream_tag,
                            downstream_node_name, 
                            parallel_edge.downstream_tag
                        ))
                        
                    except Exception as e:
                        self.logger.error(f"Error setting up connection {node_name} -> {downstream_node_name}: {e}")
                        raise        

    def create_node_instance(self, graph_node: GraphNode) -> Union[ActorHandle, LocalDAGNode]:
        """
        根据图节点创建对应的执行实例
        
        Args:
            graph_node: 图节点对象
            
        Returns:
            节点实例（Ray Actor或本地节点）
        """
        transformation = graph_node.transformation
        platform = self.env.config.get("platform", "local")  # 默认使用本地平台
        memory_collection = self.env.memory_collection
        if platform == "remote":
            node = RayDAGNode.remote(
                graph_node.name,
                transformation,
                self.session_folder,
                memory_collection
            )
            self.logger.debug(f"Created Ray actor node: {graph_node.name}")
        else:
            # 创建本地节点
            node = LocalDAGNode(
                graph_node.name,
                transformation,
                memory_collection
            )
            self.logger.debug(f"Created local node: {graph_node.name}")
        
        from sage_core.core.operator.transformation import TransformationType
        if(transformation.type == TransformationType.SOURCE):
            self.spout_nodes.append(graph_node.name)
            self.logger.debug(f"Node '{graph_node.name}' is a spout node")

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
        
        for node_name, node_handle in self.name_to_DAGnode.items():
            if isinstance(node_handle, LocalDAGNode):
                node = self.name_to_DAGnode[node_name]
                node.start()
                local_node_count += 1
                self.logger.debug(f"Started local node: {node_name}")
            else:
                ray_node_count += 1
        
        self.logger.info(f"Started {local_node_count} local nodes, {ray_node_count} Ray actors")

    def stop_all_nodes(self):
        """停止所有节点"""
        self.logger.info("Stopping all DAG nodes...")
        
        for node_name, node_meta in self.name_to_DAGnode.items():
            try:
                if isinstance(node_meta, ActorHandle) == False:
                    # local
                    node = self.name_to_DAGnode[node_name]
                    node.stop()
                    self.logger.debug(f"Stopped local node: {node_name}")
                # Ray actors会在进程结束时自动清理
            except Exception as e:
                self.logger.error(f"Error stopping node {node_name}: {e}")
    
    def submit(self):
        self.logger.info(f"Submitting MixedDAG '{self.name}'")
        try:
            for node_name, node_handle in self.name_to_DAGnode.items():
                if( node_name in self.spout_nodes):
                    self.logger.debug(f"Node '{node_name}' is a spout node, skipping submission")
                    continue
                if isinstance(node_handle, LocalDAGNode):
                    local_runtime = LocalRuntime.get_instance()
                    local_runtime.submit_node(node_handle)
                    self.logger.debug(f"Submitted local node: {node_name}")
                elif isinstance(node_handle, ActorHandle):
                    ray_runtime = RayRuntime.get_instance()
                    ray_runtime.submit_actor_instance(node_handle, node_name)
                    self.logger.debug(f"Submitted Ray actor: {node_name}")
        except Exception as e:
            self.logger.error(f"Failed to submit MixedDAG '{self.name}': {e}", exc_info=True)
            # 清理已经提交的节点
            # self._cleanup_partial_submission(local_runtime, ray_runtime)
            raise

    def execute_once(self, spout_node_name:str = None):
        self.logger.info(f"executing once")
        if(spout_node_name is None):
            for node_name in self.spout_nodes:
                node_handle = self.name_to_DAGnode[node_name]
                if isinstance(node_handle, LocalDAGNode):
                    self.logger.debug(f"Running spout node: {node_name}")

                    node_handle.run_once()
                elif isinstance(node_handle, ActorHandle):
                    self.logger.debug(f"Running remote spout node: {node_name}")

                    # Ray Actor执行一次
                    node_handle.run_once.remote()
        else:
            if spout_node_name in self.spout_nodes:
                node_handle = self.name_to_DAGnode[spout_node_name]
                if isinstance(node_handle, LocalDAGNode):
                    self.logger.debug(f"Running spout node: {node_name}")

                    node_handle.run_once()
                elif isinstance(node_handle, ActorHandle):
                    self.logger.debug(f"Running remote spout node: {node_name}")

                    # Ray Actor执行一次
                    node_handle.run_once.remote()
            else:
                self.logger.warning(f"Spout node '{spout_node_name}' not found in MixedDAG '{self.name}'")

    def execute_streaming(self, spout_node_name:str = None):
        self.logger.info(f"executing streaming")
        if(spout_node_name is None):
            for node_name in self.spout_nodes:
                node_handle = self.name_to_DAGnode[node_name]
                if isinstance(node_handle, LocalDAGNode):
                    node_handle.run_loop()
                elif isinstance(node_handle, ActorHandle):
                    # Ray Actor执行一次
                    node_handle.run_loop.remote()
        else:
            if spout_node_name in self.spout_nodes:
                node_handle = self.name_to_DAGnode[spout_node_name]
                if isinstance(node_handle, LocalDAGNode):
                    node_handle.run_loop()
                elif isinstance(node_handle, ActorHandle):
                    # Ray Actor执行一次
                    node_handle.run_loop.remote()
            else:
                self.logger.warning(f"Spout node '{spout_node_name}' not found in MixedDAG '{self.name}'")

    def run(self) -> Dict[str, List[str]]: # deprecated
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
            # 分离本地节点和Ray节点
            local_nodes = []
            ray_actors = []
            ray_node_names = []
            
            for node_name, node_handle in self.name_to_DAGnode.items():
                if isinstance(node_handle, LocalDAGNode):
                    local_node = self.name_to_DAGnode[node_name]
                    local_nodes.append(local_node)
                elif isinstance(node_handle, ActorHandle):
                    ray_actor = self.name_to_DAGnode[node_name]
                    ray_actors.append(ray_actor)
                    ray_node_names.append(node_name)
            
            # 提交本地节点到LocalRuntime
            if local_nodes:
                self.logger.info(f"Submitting {len(local_nodes)} local nodes to LocalRuntime")
                local_runtime = LocalRuntime.get_instance()
                self.local_handles = local_runtime.submit_nodes(local_nodes)
                
                # 注册本地节点到TCP服务器（用于接收Ray Actor的数据）
                for local_node in local_nodes:
                    # 这里需要确保local_runtime知道节点名称映射
                    # 实际上submit_nodes已经在running_nodes中注册了
                    pass
                
                self.logger.info(f"Successfully submitted local nodes with handles: {self.local_handles}")
            
            # 提交Ray节点到RayRuntime
            if ray_actors:
                ray_runtime = RayRuntime.get_instance()
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

    def debug_print_operators(self):
        """
        调试方法：打印MixedDAG中所有operators的详细信息，包括名字、类型、平台等
        """
        lines = []
        lines.append("\n")
        lines.append("=" * 80)
        lines.append(f"MixedDAG Operators Debug Information for '{self.name}'")
        lines.append("=" * 80)
        
        if not self.name_to_DAGnode:
            lines.append("No operators in the MixedDAG")
            self.logger.debug("\n".join(lines))
            return
        
        # 统计信息
        local_count = 0
        ray_count = 0
        unknown_count = 0
        
        # 按平台类型分组
        local_operators = []
        ray_operators = []
        unknown_operators = []
        
        for node_name, operator in self.name_to_DAGnode.items():
            platform_type = self._detect_platform(operator)
            
            if platform_type == "local":
                local_operators.append((node_name, operator))
                local_count += 1
            elif platform_type == "remote":
                ray_operators.append((node_name, operator))
                ray_count += 1
            else:
                unknown_operators.append((node_name, operator))
                unknown_count += 1
        
        # 显示统计信息
        lines.append(f"\n📊 Operators Statistics:")
        lines.append(f"   Total Operators: {len(self.name_to_DAGnode)}")
        lines.append(f"   Local Nodes: {local_count}")
        lines.append(f"   Ray Actors: {ray_count}")
        if unknown_count > 0:
            lines.append(f"   Unknown Type: {unknown_count}")
        lines.append(f"   Total Connections: {len(self.connections)}")
        lines.append(f"   Running Status: {self.is_running}")
        
        # 显示本地节点
        if local_operators:
            lines.append(f"\n🏠 Local Operators ({local_count}):")
            for node_name, operator in local_operators:
                lines.append(f"   📍 Node: {node_name}")
                lines.append(f"      Type: LocalDAGNode")
                lines.append(f"      Class: {operator.__class__.__name__}")
                lines.append(f"      Platform: local")
                
                # 显示transformation信息
                if hasattr(operator, 'transformation'):
                    transformation = operator.transformation
                    lines.append(f"      Transformation: {transformation.type.value}")
                    lines.append(f"      Function: {transformation.function_class.__name__}")
                    lines.append(f"      Parallelism: {transformation.parallelism}")
                
                # 显示运行状态
                if hasattr(operator, 'is_running'):
                    lines.append(f"      Status: {'Running' if operator.is_running else 'Stopped'}")
                
                lines.append("")
        
        # 显示Ray节点
        if ray_operators:
            lines.append(f"\n☁️ Ray Operators ({ray_count}):")
            for node_name, operator in ray_operators:
                lines.append(f"   📍 Node: {node_name}")
                lines.append(f"      Type: ActorHandle")
                lines.append(f"      Class: {operator.__class__.__name__}")
                lines.append(f"      Platform: remote")
                lines.append(f"      Actor ID: {str(operator)}")
                
                # 从graph中获取transformation信息
                if node_name in self.graph.nodes:
                    graph_node = self.graph.nodes[node_name]
                    transformation = graph_node.transformation
                    lines.append(f"      Transformation: {transformation.type.value}")
                    lines.append(f"      Function: {transformation.function_class.__name__}")
                    lines.append(f"      Parallelism: {transformation.parallelism}")
                
                lines.append("")
        
        # 显示未知类型节点
        if unknown_operators:
            lines.append(f"\n❓ Unknown Type Operators ({unknown_count}):")
            for node_name, operator in unknown_operators:
                lines.append(f"   📍 Node: {node_name}")
                lines.append(f"      Type: {type(operator).__name__}")
                lines.append(f"      Class: {operator.__class__.__name__}")
                lines.append(f"      Platform: unknown")
                lines.append("")
        
        # 显示连接信息
        lines.append(f"\n🔗 Connections ({len(self.connections)}):")
        if self.connections:
            for upstream_node, out_channel, downstream_node, in_channel in self.connections:
                upstream_type = self._detect_platform(self.name_to_DAGnode[upstream_node])
                downstream_type = self._detect_platform(self.name_to_DAGnode[downstream_node])
                lines.append(f"   {upstream_node}({upstream_type})[{out_channel}] -> {downstream_node}({downstream_type})[{in_channel}]")
        else:
            lines.append("   No connections established")
        
        # 显示句柄信息
        lines.append(f"\n🔧 Runtime Handles:")
        lines.append(f"   Local Handles: {len(self.local_handles)} - {self.local_handles}")
        lines.append(f"   Ray Handles: {len(self.ray_handles)} - {self.ray_handles}")
        
        # 显示会话信息
        lines.append(f"\n📁 Session Information:")
        lines.append(f"   Session Folder: {self.session_folder}")
        lines.append(f"   Environment: {self.env.name}")
        lines.append(f"   Environment Config: {self.env.config}")
        
        lines.append("=" * 80)
        
        # 一次性输出所有调试信息
        self.logger.debug("\n".join(lines))