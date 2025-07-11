from typing import Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
from sage_runtime.dagnode.base_dag_node import BaseDAGNode
from sage_runtime.dagnode.local_dag_node import LocalDAGNode
from sage_runtime.dagnode.ray_dag_node import RayDAGNode
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
                 broadcast_index: int,
                 parallel_index: int,
                 target_name: str,
                 target_node: Union[ActorHandle, LocalDAGNode],
                 tcp_server: LocalTcpServer):

        self.broadcast_index: int = broadcast_index
        self.parallel_index: int = parallel_index
        self.target_name: str = target_name

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

    def _build_target_config(self, target_node: BaseDAGNode, 
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
