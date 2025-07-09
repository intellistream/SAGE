import ray
import time
from typing import Any, Dict, Union, TYPE_CHECKING
from ray.actor import ActorHandle
from sage_runtime.operator.runtime_context import RuntimeContext
from sage_runtime.executor.base_dag_node import BaseDAGNode
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:   
    from sage_core.core.operator.base_operator import BaseOperator
    from sage_runtime.operator.factory import OperatorFactory
    from sage_runtime.operator.operator_wrapper import OperatorWrapper

class RayDAGNode(BaseDAGNode):
    """
    Ray Actor version of LocalDAGNode for distributed execution.
    
    Unlike local nodes, Ray actors don't need input buffers as Ray platform
    maintains the request queue for actors automatically.
    """
    
    def __init__(self, name: str, operator_factory: 'OperatorFactory' ,memory_collection:ActorHandle = None) -> None:
        if(not isinstance(memory_collection, ActorHandle)):
            raise Exception("Memory collection must be a Ray Actor handle")
        super().__init__(name)
        self.operator:'OperatorWrapper' = operator_factory.build_instance(name = name, remote = True)
        self.is_spout = operator_factory.is_spout  # Check if this is a spout node
        self.memory_collection = memory_collection  # Optional memory collection for this node
        self.operator.insert_runtime_context(RuntimeContext(self.memory_collection))

        # Running state management
        self._stop_requested = False
        self.logger.info(f"Created Ray actor node: {self.name}")

    



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
                    self.operator.process_data(None, None)
                    time.sleep(1)  # Small delay to prevent overwhelming
                        
                except Exception as e:
                    self.logger.error(f"Error in spout node {self.name}: {e}", exc_info=True)
                    raise
            self._running = False
            self.logger.info(f"Spout execution stopped for node {self.name}")
        else:
            # For non-spout nodes, just mark as running

            self.logger.info(f"Ray node {self.name} started and ready to receive data")


    ########################################################
    #                inactive methods                      #
    ########################################################

    def get_node_info(self) -> Dict[str, Any]:
        """Get comprehensive node information for debugging."""
        return {
            "name": self.name,
            "is_spout": self.is_spout,
            "is_running": self.is_running(),
            "stop_requested": self._stop_requested,
            "initialized": self._initialized,
            "operator_class": self.function_class.__name__ if self.function_class else None,
            "downstream_targets": len(self.emit_context.downstream_channels) if hasattr(self, 'emit_context') else 0
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        try:
            return {
                "status": "healthy",
                "node_name": self.name,
                "is_running": self.is_running(),
                "initialized": self._initialized,
                "timestamp": time.time_ns()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "node_name": self.name,
                "error": str(e),
                "timestamp": time.time_ns()
            }

    def __getstate__(self):
        """
        Custom serialization to exclude non-serializable objects.
        Ray handles most serialization automatically, but this helps with debugging.
        """
        state = self.__dict__.copy()
        # Ray actors typically don't need custom serialization,
        # but we can exclude logger if needed
        return state

    def __setstate__(self, state):
        """
        Custom deserialization to restore state.
        """
        self.__dict__.update(state)
        # Mark as not initialized so sage_runtime objects will be created when needed
        self._initialized = False