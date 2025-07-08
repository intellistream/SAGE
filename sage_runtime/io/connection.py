from dataclasses import dataclass
from enum import Enum
from sage_runtime.executor.local_dag_node import LocalDAGNode
from sage_runtime.executor.ray_dag_node import RayDAGNode
from sage_runtime.executor.base_dag_node import BaseDagNode
from ray.actor import ActorHandle
from sage_runtime.io.local_tcp_server import LocalTcpServer
from typing import Union
class NodeType(Enum):
    LOCAL = "local"
    RAY_ACTOR = "ray_actor"

class Connection(dataclass):
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

        self.own_type: NodeType
        self.output_tag: str = output_tag
        self.broadcast_index: int = broadcast_index
        self.parallel_index: int = parallel_index

        self.target_name: str = target_name
        self.target_input_tag: str = target_input_tag
        self.target_type: NodeType
        self.target_config: dict

    # def inject_config(self, own_node: Union[ActorHandle, LocalDAGNode], target_node: Union[ActorHandle, LocalDAGNode]):

        if isinstance(own_node, LocalDAGNode):
            self.own_type = NodeType.LOCAL
        elif isinstance(own_node, ActorHandle):
            self.own_type = NodeType.RAY_ACTOR
        else:
            raise NotImplementedError(f"未知节点类型: {type(own_node)}")
        if isinstance(target_node, LocalDAGNode):
            self.target_type = NodeType.LOCAL
        elif isinstance(target_node, ActorHandle):
            self.target_type = NodeType.RAY_ACTOR
        else:
            raise NotImplementedError(f"未知节点类型: {type(target_node)}")



        # 根据 own_type 和 target_type 自动推断 config 内容
        if self.own_type is NodeType.LOCAL:
            if self.target_type is NodeType.LOCAL:
                # 本地到本地的连接
                self.target_config = {"dagnode": target_node}

            elif self.target_type is NodeType.RAY_ACTOR:
                # 本地到Ray Actor的连接
                self.target_config = {"actorhandle": target_node,}

            else:
                raise NotImplementedError(f"未知连接类型: {self.own_type} → {self.target_type}")
            
        elif self.own_type is NodeType.RAY_ACTOR:

            if self.target_type is NodeType.LOCAL:
                self.target_config = {
                    "tcp_host": tcp_server.host,
                    "tcp_port": tcp_server.port
                }
            elif self.target_type is NodeType.RAY_ACTOR:
                # 本地到Ray Actor的连接
                self.target_config = {"actorhandle": target_node,}
            else:
                raise NotImplementedError(f"未知连接类型: {self.own_type} → {self.target_type}")