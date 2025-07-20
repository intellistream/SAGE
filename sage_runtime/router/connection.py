from typing import Union, TYPE_CHECKING, Any
from dataclasses import dataclass
from enum import Enum
from sage_utils.local_message_queue import LocalMessageQueue
from ray.actor import ActorHandle

@dataclass
class Connection:
    """
    用于表示本地节点和Ray Actor之间的连接
    """
    def __init__(self,
                 broadcast_index: int,
                 parallel_index: int,
                 target_name: str,
                 target_input_buffer: Union[ActorHandle, LocalMessageQueue],
                 target_input_index: int):

        self.broadcast_index: int = broadcast_index
        self.parallel_index: int = parallel_index
        self.target_name: str = target_name
        self.target_buffer: Union[ActorHandle, LocalMessageQueue] = target_input_buffer
        self.target_input_index: int = target_input_index