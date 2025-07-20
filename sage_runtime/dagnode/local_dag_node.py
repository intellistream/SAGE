from __future__ import annotations
import time, copy
from typing import Any, Union, Tuple, TYPE_CHECKING
from sage_runtime.io.local_message_queue import LocalMessageQueue
from sage_runtime.dagnode.base_dag_node import BaseDAGNode
from ray.actor import ActorHandle
from sage_memory.memory_collection.base_collection import BaseMemoryCollection
from sage_utils.custom_logger import CustomLogger

if TYPE_CHECKING:
    from sage_core.transformation.base_transformation import BaseTransformation
    from sage_runtime.operator.factory import OperatorFactory
    from sage_core.operator.base_operator import BaseOperator
    from sage_runtime.operator.operator_wrapper import OperatorWrapper
    from sage_runtime.compiler import Compiler, GraphNode
    from sage_runtime.runtime_context import RuntimeContext



class LocalDAGNode(BaseDAGNode):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.input_buffer = LocalMessageQueue(name = self.name, env_name=self.runtime_context.env_name)  # Local input buffer for this node
        self.logger.info(f"Initialized LocalDAGNode: {self.name} (spout: {self.is_spout})")
