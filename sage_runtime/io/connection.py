from typing import Union, TYPE_CHECKING, Any
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
                 broadcast_index: int,
                 parallel_index: int,
                 target_name: str,
                 target_input_buffer: Union[ActorHandle, LocalDAGNode],
                 target_input_index: int):

        self.broadcast_index: int = broadcast_index
        self.parallel_index: int = parallel_index
        self.target_name: str = target_name
        self.target_buffer: Union[ActorHandle, Any] = target_input_buffer
        self.target_input_index: int = target_input_index