from typing import Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
from sage_runtime.executor.local_dag_node import LocalDAGNode
from sage_runtime.executor.ray_dag_node import RayDAGNode
from ray.actor import ActorHandle
from sage_runtime.io.local_tcp_server import LocalTcpServer
class NodeType(Enum):
    LOCAL = "local"
    RAY_ACTOR = "ray_actor"

class ConnectionType(Enum):
    LOCAL_TO_LOCAL = "local_to_local"
    LOCAL_TO_RAY = "local_to_ray"
    RAY_TO_LOCAL = "ray_to_local"
    RAY_TO_RAY = "ray_to_ray"

@dataclass
class Connection:
    """
    用于表示本地节点和Ray Actor之间的连接
    """
    def __init__(self,
                 own_node: Union[ActorHandle, LocalDAGNode],
                 output_tag: str,
                 broadcast_index: int,
                 parallel_index: int,
                 target_name: str,
                 target_node: Union[ActorHandle, LocalDAGNode],
                 target_input_tag: str,
                 tcp_server: LocalTcpServer):

        self.output_tag: str = output_tag
        self.broadcast_index: int = broadcast_index
        self.parallel_index: int = parallel_index
        self.target_name: str = target_name
        self.target_input_tag: str = target_input_tag

        # 统一的节点类型检测
        self.own_type: NodeType = self._detect_node_type(own_node)
        self.target_type: NodeType = self._detect_node_type(target_node)
        
        # 根据连接类型构建配置
        self.connection_type: ConnectionType = self._get_connection_type()
        self.target_config: dict = self._build_target_config(target_node, tcp_server)

    def _detect_node_type(self, node: Union[ActorHandle, LocalDAGNode]) -> NodeType:
        """
        统一的节点类型检测方法
        
        Args:
            node: 要检测的节点对象
            
        Returns:
            NodeType: 节点类型枚举
            
        Raises:
            NotImplementedError: 当节点类型未知时
        """
        if isinstance(node, LocalDAGNode):
            return NodeType.LOCAL
        elif isinstance(node, RayDAGNode):
            return NodeType.RAY_ACTOR
        else:
            raise NotImplementedError(f"未知节点类型: {type(node)}")

    def _get_connection_type(self) -> ConnectionType:
        """
        根据源节点和目标节点类型确定连接类型
        
        Returns:
            ConnectionType: 连接类型枚举
        """
        if self.own_type == NodeType.LOCAL and self.target_type == NodeType.LOCAL:
            return ConnectionType.LOCAL_TO_LOCAL
        elif self.own_type == NodeType.LOCAL and self.target_type == NodeType.RAY_ACTOR:
            return ConnectionType.LOCAL_TO_RAY
        elif self.own_type == NodeType.RAY_ACTOR and self.target_type == NodeType.LOCAL:
            return ConnectionType.RAY_TO_LOCAL
        elif self.own_type == NodeType.RAY_ACTOR and self.target_type == NodeType.RAY_ACTOR:
            return ConnectionType.RAY_TO_RAY
        else:
            raise NotImplementedError(f"未知连接类型: {self.own_type} → {self.target_type}")

    def _build_target_config(self, target_node: Union[ActorHandle, LocalDAGNode], 
                           tcp_server: LocalTcpServer) -> dict:
        """
        根据连接类型构建目标配置字典
        
        Args:
            target_node: 目标节点对象
            tcp_server: TCP服务器对象
            
        Returns:
            dict: 目标配置字典
        """
        if self.connection_type == ConnectionType.LOCAL_TO_LOCAL:
            # 本地到本地的连接
            return {
                "type": "direct_local",
                "dagnode": target_node,
                "node_name": self.target_name
            }

        elif self.connection_type == ConnectionType.LOCAL_TO_RAY:
            # 本地到Ray Actor的连接
            return {
                "type": "actor_handle",
                "actorhandle": target_node.operator.get_wrapped_operator(),
                "node_name": self.target_name
            }

        elif self.connection_type == ConnectionType.RAY_TO_LOCAL:
            # Ray Actor到本地的连接
            return {
                "type": "local_tcp",
                "node_name": self.target_name,
                "tcp_host": tcp_server.host,
                "tcp_port": tcp_server.port
            }

        elif self.connection_type == ConnectionType.RAY_TO_RAY:
            # Ray Actor到Ray Actor的连接
            return {
                "type": "actor_handle",
                "actorhandle": target_node.operator.get_wrapped_operator(),
                "node_name": self.target_name
            }

        else:
            raise NotImplementedError(f"未知连接类型: {self.connection_type}")

    def debug_info(self) -> str:
        """
        返回连接的详细调试信息
        
        Returns:
            str: 格式化的调试信息字符串
        """
        info_lines = []
        info_lines.append("=" * 60)
        info_lines.append("🔗 Connection Debug Information")
        info_lines.append("=" * 60)
        
        # 基本连接信息
        info_lines.append(f"📡 Connection Type: {self.connection_type.value}")
        info_lines.append(f"🏷️  Output Tag: '{self.output_tag}'")
        info_lines.append(f"📊 Broadcast Index: {self.broadcast_index}")
        info_lines.append(f"🔢 Parallel Index: {self.parallel_index}")
        
        # 源节点信息
        info_lines.append("")
        info_lines.append("📤 Source Node:")
        info_lines.append(f"   Type: {self.own_type.value}")
        info_lines.append(f"   Output Tag: '{self.output_tag}'")
        
        # 目标节点信息
        info_lines.append("")
        info_lines.append("📥 Target Node:")
        info_lines.append(f"   Name: '{self.target_name}'")
        info_lines.append(f"   Type: {self.target_type.value}")
        info_lines.append(f"   Input Tag: '{self.target_input_tag}'")
        
        # 目标配置信息
        info_lines.append("")
        info_lines.append("⚙️  Target Configuration:")
        for key, value in self.target_config.items():
            if key == "dagnode":
                info_lines.append(f"   {key}: <LocalDAGNode: {getattr(value, 'name', 'unknown')}>")
            elif key == "actorhandle":
                info_lines.append(f"   {key}: <ActorHandle: {self.target_name}>")
            else:
                info_lines.append(f"   {key}: {value}")
        
        # 连接路径可视化
        info_lines.append("")
        info_lines.append("🛤️  Connection Path:")
        path = f"   [{self.own_type.value}][{self.output_tag}] "
        path += f"--({self.connection_type.value})--> "
        path += f"[{self.target_type.value}:{self.target_name}][{self.target_input_tag}]"
        info_lines.append(path)
        
        info_lines.append("=" * 60)
        
        return "\n".join(info_lines)

    def print_debug_info(self):
        """
        打印连接的调试信息到控制台
        """
        print(self.debug_info())

    def get_summary(self) -> str:
        """
        获取连接的简短摘要信息
        
        Returns:
            str: 连接摘要字符串
        """
        return (f"{self.connection_type.value}: "
                f"[{self.output_tag}] -> {self.target_name}[{self.target_input_tag}] "
                f"(broadcast:{self.broadcast_index}, parallel:{self.parallel_index})")

    def is_cross_platform(self) -> bool:
        """
        检查这是否是跨平台连接（本地到Ray或Ray到本地）
        
        Returns:
            bool: 如果是跨平台连接返回True
        """
        return (self.connection_type == ConnectionType.LOCAL_TO_RAY or 
                self.connection_type == ConnectionType.RAY_TO_LOCAL)

    def requires_tcp(self) -> bool:
        """
        检查连接是否需要TCP通信
        
        Returns:
            bool: 如果需要TCP通信返回True
        """
        return self.connection_type == ConnectionType.RAY_TO_LOCAL

    def __str__(self) -> str:
        """字符串表示"""
        return self.get_summary()

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"Connection(type={self.connection_type.value}, "
                f"output='{self.output_tag}', target='{self.target_name}', "
                f"input='{self.target_input_tag}', "
                f"broadcast={self.broadcast_index}, parallel={self.parallel_index})")