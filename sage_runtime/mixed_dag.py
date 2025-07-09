from typing import Dict, List, Any, Tuple, Union, TYPE_CHECKING
from ray.actor import ActorHandle

from sage_runtime.runtimes.local_runtime import LocalRuntime
# from sage_runtime.runtimes.ray_runtime import RayRuntime
from sage_runtime.executor.local_dag_node import LocalDAGNode
from sage_runtime.executor.ray_dag_node import RayDAGNode
from sage_runtime.executor.base_dag_node import BaseDAGNode
from sage_runtime.io.local_tcp_server import LocalTcpServer
from sage_runtime.io.connection import Connection
from sage_utils.custom_logger import CustomLogger
from sage_core.core.compiler import Compiler, GraphNode

if TYPE_CHECKING:
    from sage_core.api.env import BaseEnvironment 


class MixedDAG():
    def __init__(self, graph: Compiler, env:'BaseEnvironment'):
        self.graph = graph
        self.name:str = graph.name
        self.logger = CustomLogger(
            filename=f"MixedDAG_{self.name}",
            console_output="WARNING",
            file_output="DEBUG",
            global_output = "DEBUG",
        )
        # self.nodes: Dict[str, Union[ActorHandle, LocalDAGNode]] = {}
        self.nodes: Dict[str, BaseDAGNode] = {}

        self.spout_nodes: List[str] = []

        self.connections: List[Connection] = []
        self.session_folder = CustomLogger.get_session_folder()

        self.is_running: bool = False

        # 为这个 DAG 分配独立的 TCP 端口
        self.tcp_server = LocalTcpServer(
            # host="localhost",
            # port=self.tcp_port,
            message_handler=self._handle_tcp_message
        )
        # self.tcp_server.start()

        self._compile_graph(graph, env)
        self.debug_print_operators()
        # 启动 TCP 服务器
        self.logger.info(f"MixedDAG '{self.name}' construction complete")
    

        

    
    def _compile_graph(self, graph: Compiler, env:'BaseEnvironment'):
        """编译图结构，创建节点并建立连接"""
        self.logger.info(f"Compiling mixed DAG for graph: {self.name}")
        
        # 第一步：创建所有节点实例
        for node_name, graph_node in graph.nodes.items():
            node_instance = self.create_node_instance(graph_node, env)
            # upstream_nodes = self.compiler.get_upstream_nodes(node_name)
            self.nodes[node_name] = node_instance
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
        
        for output_tag, broadcasting_groups in graph_node.output_channels.items():
            for broadcast_index, parallel_edges in enumerate(broadcasting_groups):
                for parallel_index, parallel_edge in enumerate(parallel_edges):
                    target_name = parallel_edge.downstream_node.name
                    target_handle = self.nodes[target_name]

                    connection = Connection(
                        own_node=output_handle,
                        output_tag=output_tag,
                        broadcast_index=broadcast_index,
                        parallel_index=parallel_index,
                        target_name=target_name,
                        target_node=target_handle,
                        target_input_tag=parallel_edge.downstream_tag,
                        tcp_server=self.tcp_server
                    )
                    try:
                        if isinstance(output_handle, ActorHandle):
                            
                            output_handle.add_connection.remote(connection)
                            self.logger.debug(f"Setup Ray connection: {node_name}[{output_tag}] -> {target_name}[{parallel_edge.downstream_tag}]")
                        else:
                            # 本地节点直接调用
                            output_handle.add_connection(connection)
                            self.logger.debug(f"Setup local connection: {node_name}[{output_tag}] -> {target_name}[{parallel_edge.downstream_tag}]")
                            
                        # 记录连接信息
                        self.connections.append(connection)
                        
                    except Exception as e:
                        self.logger.error(f"Error setting up connection {node_name} -> {target_name}: {e}")
                        raise        

    def create_node_instance(self, graph_node: GraphNode, env:'BaseEnvironment') -> BaseDAGNode:
        """
        根据图节点创建对应的执行实例
        
        Args:
            graph_node: 图节点对象
            
        Returns:
            节点实例（Ray Actor或本地节点）
        """
        transformation = graph_node.transformation
        memory_collection = env.memory_collection
        from sage_core.api.enum import PlatformType

        if env.platform == PlatformType.REMOTE:
            node = RayDAGNode(
                graph_node,
                transformation.operator_factory,
                memory_collection
            )
            self.logger.debug(f"Created remote node: {graph_node.name}")
        else:
            # 创建本地节点
            node = LocalDAGNode(
                graph_node,
                transformation.operator_factory,
                memory_collection
            )
            self.logger.debug(f"Created local node: {graph_node.name}")
        
        from sage_core.api.transformation import TransformationType
        if(transformation.type == TransformationType.SOURCE):
            self.spout_nodes.append(graph_node.name)
            self.logger.debug(f"Node '{graph_node.name}' is a spout node")

        return node

    def stop(self):
        if(not self.is_running):
            self.logger.warning(f"MixedDAG '{self.name}' is not running, nothing to stop")
            return
        
        for node_name in self.spout_nodes:
            node = self.nodes[node_name]
            node.stop()
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
                local_runtime = LocalRuntime.get_instance()
                local_runtime.submit_node(node)
        except Exception as e:
            self.logger.error(f"Failed to submit MixedDAG '{self.name}': {e}", exc_info=True)

    def execute_once(self, spout_node_name:str = None):
        self.logger.info(f"executing once")
        if(spout_node_name is None):
            for node_name in self.spout_nodes:
                node = self.nodes[node_name]
                node.process()
        elif spout_node_name in self.spout_nodes:
            node = self.nodes[spout_node_name]
            self.logger.debug(f"Running spout node: {node_name}")
            node.process()
        else:
            self.logger.warning(f"Spout node '{spout_node_name}' not found in MixedDAG '{self.name}'")

    def execute_streaming(self, spout_node_name:str = None):
        self.logger.info(f"executing streaming")
        self.is_running = True
        if(spout_node_name is None):
            for node_name in self.spout_nodes:
                node_handle = self.nodes[node_name]
                local_runtime = LocalRuntime.get_instance()
                local_runtime.submit_node(node_handle)
                self.logger.debug(f"Running spout node: {node_name}")
        elif spout_node_name in self.spout_nodes:
            node_handle = self.nodes[spout_node_name]
            local_runtime = LocalRuntime.get_instance()
            local_runtime.submit_node(node_handle)
            self.logger.debug(f"Running spout node: {node_name}")
        else:
            self.logger.warning(f"Spout node '{spout_node_name}' not found in MixedDAG '{self.name}'")

    def debug_print_operators(self):
        """
        调试方法：打印MixedDAG中所有operators的详细信息，包括名字、类型、平台等
        """
        lines = []
        lines.append("\n")
        lines.append("=" * 80)
        lines.append(f"MixedDAG Operators Debug Information for '{self.name}'")
        lines.append("=" * 80)
        
        if not self.nodes:
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
        
        for node_name, operator in self.nodes.items():
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
        lines.append(f"   Total Operators: {len(self.nodes)}")
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
        
        # 显示连接信息 - 重写这部分以使用新的Connection对象
        lines.append(f"\n🔗 Connections Summary ({len(self.connections)}):")
        if self.connections:
            # 按连接类型分组统计
            connection_stats = {}
            cross_platform_connections = []
            tcp_connections = []
            
            for connection in self.connections:
                conn_type = connection.connection_type.value
                if conn_type not in connection_stats:
                    connection_stats[conn_type] = 0
                connection_stats[conn_type] += 1
                
                # 收集跨平台连接
                if connection.is_cross_platform():
                    cross_platform_connections.append(connection)
                
                # 收集TCP连接
                if connection.requires_tcp():
                    tcp_connections.append(connection)
            
            # 显示连接类型统计
            lines.append(f"   📈 Connection Type Statistics:")
            for conn_type, count in connection_stats.items():
                lines.append(f"      {conn_type}: {count}")
            
            lines.append(f"   🌉 Cross-platform connections: {len(cross_platform_connections)}")
            lines.append(f"   🌐 TCP connections: {len(tcp_connections)}")
            
            # 显示详细连接信息
            lines.append(f"\n🔗 Detailed Connections:")
            for i, connection in enumerate(self.connections, 1):
                # 基本连接信息
                source_platform = connection.own_type.value
                target_platform = connection.target_type.value
                
                lines.append(f"   #{i:02d}: {connection.get_summary()}")
                lines.append(f"        📤 Source: {source_platform}")
                lines.append(f"        📥 Target: {target_platform}")
                
                # 如果是跨平台连接，显示特殊标记
                if connection.is_cross_platform():
                    lines.append(f"        🌉 Cross-platform connection")
                
                # 如果需要TCP，显示TCP配置
                if connection.requires_tcp():
                    tcp_config = connection.target_config
                    lines.append(f"        🌐 TCP: {tcp_config.get('tcp_host')}:{tcp_config.get('tcp_port')}")
                
                # 显示广播和并行信息
                if connection.broadcast_index > 0 or connection.parallel_index > 0:
                    lines.append(f"        📊 Routing: broadcast[{connection.broadcast_index}], parallel[{connection.parallel_index}]")
                
                lines.append("")
            
            # 显示连接拓扑图（简化版）
            lines.append(f"\n🗺️  Connection Topology:")
            # 按源节点分组显示连接
            connections_by_source = {}
            for connection in self.connections:
                source_name = None
                # 从节点字典中找到源节点名称
                for node_name, node_handle in self.nodes.items():
                    if (isinstance(node_handle, ActorHandle) and connection.own_type.value == "ray_actor") or \
                    (isinstance(node_handle, LocalDAGNode) and connection.own_type.value == "local"):
                        # 这里需要更精确的匹配逻辑，暂时使用启发式方法
                        if connection.target_name != node_name:  # 排除自环
                            source_name = node_name
                            break
                
                # 如果无法确定源节点，使用连接信息推断
                if source_name is None:
                    # 从connections列表中找到包含target_name作为下游的连接
                    for other_conn in self.connections:
                        if other_conn.target_name == connection.target_name:
                            continue
                    # 简化处理：直接使用第一个非目标节点
                    for node_name in self.nodes.keys():
                        if node_name != connection.target_name:
                            source_name = node_name
                            break
                
                if source_name not in connections_by_source:
                    connections_by_source[source_name] = []
                connections_by_source[source_name].append(connection)
            
            for source_name, source_connections in connections_by_source.items():
                source_platform = self._detect_platform(self.nodes[source_name])
                lines.append(f"   📍 {source_name} ({source_platform}):")
                
                for connection in source_connections:
                    target_platform = connection.target_type.value
                    connection_symbol = self._get_connection_symbol(connection.connection_type.value)
                    lines.append(f"      {connection_symbol} {connection.target_name} ({target_platform}) "
                            f"[{connection.output_tag}→{connection.target_input_tag}]")
            
        else:
            lines.append("   No connections established")
        
        # 显示会话信息
        lines.append(f"\n📁 Session Information:")
        lines.append(f"   Session Folder: {self.session_folder}")
        lines.append(f"   TCP Server: {self.tcp_server.host}:{self.tcp_server.port}")
        
        lines.append("=" * 80)
        
        # 一次性输出所有调试信息
        self.logger.debug("\n".join(lines))

    def _get_connection_symbol(self, connection_type: str) -> str:
        """
        根据连接类型返回对应的符号
        
        Args:
            connection_type: 连接类型字符串
            
        Returns:
            str: 连接符号
        """
        symbols = {
            "local_to_local": "🔗",      # 本地到本地
            "local_to_ray": "📤",        # 本地到远程
            "ray_to_local": "📥",        # 远程到本地
            "ray_to_ray": "☁️"           # 远程到远程
        }
        return symbols.get(connection_type, "❓")

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
                input_tag = message["input_tag"]
                data = message["data"]
                source_actor = message.get("source_actor", "unknown")
                
                # 查找目标节点（在当前 DAG 中）
                if target_node_name in self.nodes:
                    target_node = self.nodes[target_node_name]
                    
                    # 确保是本地节点
                    if isinstance(target_node, LocalDAGNode):
                        # 将数据放入目标节点的输入缓冲区
                        data_packet = (input_tag, data)
                        target_node.put(data_packet)
                        
                        self.logger.debug(f"[DAG {self.name}] Delivered TCP message: {source_actor} -> "
                                        f"{target_node_name}[in:{input_tag}]")
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
