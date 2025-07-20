import ray
import time
from typing import Any, Dict, Union, TYPE_CHECKING
from ray.actor import ActorHandle
from sage_runtime.runtime_context import RuntimeContext
from sage_runtime.dagnode.base_dag_node import BaseDAGNode
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:   
    from sage_core.operator.base_operator import BaseOperator
    from sage_runtime.operator.factory import OperatorFactory
    from sage_runtime.operator.operator_wrapper import OperatorWrapper
    from sage_runtime.compiler import Compiler, GraphNode

class RayDAGNode(BaseDAGNode):
    """
    Ray Actor version of LocalDAGNode for distributed execution.
    
    Unlike local nodes, Ray actors don't need input buffers as Ray platform
    maintains the request queue for actors automatically.
    """
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def run_loop(self):
        """
        Start the node. For spout nodes, this starts the generation loop.
        For non-spout nodes, this just marks the node as ready to receive data.
        """
        self._running = True
        if self.is_spout:
            while not self.stop_event.is_set():
    
                # Start spout execution asynchronously
                try:
                    # For spout nodes, call operator.receive with dummy channel and data
                    self.operator.receive_packet(None)
                    time.sleep(self.delay)  # Small delay to prevent overwhelming
                        
                except Exception as e:
                    self.logger.error(f"Error in spout node {self.name}: {e}", exc_info=True)
                    raise
            self._running = False
            self.logger.info(f"Spout execution stopped for node {self.name}")
        else:
            # For non-spout nodes, just mark as running

            self.logger.info(f"Ray node {self.name} started and ready to receive data")