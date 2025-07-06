import ray
import time
from typing import Any, Dict, Union
from ray.actor import ActorHandle

from sage_runtime.io.ray_emit_context import RayEmitContext
from sage_core.core.operator.transformation import Transformation, TransformationType
from sage_core.core.operator.base_operator import BaseOperator
from sage_runtime.runtime_context import RuntimeContext

from sage_utils.custom_logger import CustomLogger


@ray.remote
class RayDAGNode:
    """
    Ray Actor version of LocalDAGNode for distributed execution.
    
    Unlike local nodes, Ray actors don't need input buffers as Ray platform
    maintains the request queue for actors automatically.
    """
    
    def __init__(self, name: str, transformation: Transformation,session_folder: str = None, memory_collection:ActorHandle = None) -> None:
        """
        Initialize Ray multiplexer DAG node.
        
        Args:
            name: Node name
            function_class: Operator class (not instance)
            operator_config: Configuration for operator instantiation
            is_spout: Whether this is a spout node
            session_folder: Session folder for logging
        """
        # Create logger first
        self.logger = CustomLogger(
            object_name=f"RayNode_{name}",
            session_folder=session_folder,
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        if(not isinstance(memory_collection, ActorHandle)):
            raise Exception("Memory collection must be a Ray Actor handle")
        self.memory_collection = memory_collection  # Optional memory collection for this node


        if(transformation.is_instance ):
            # ray不支持预先实例化的算子
            raise Exception("GraphNode operator must be a class for Ray platform")

        self.name = name
        self.transformation = transformation
        try:
            self.operator = transformation.build_instance(session_folder=session_folder)
            self.logger.debug(f"Created operator instance for {self.name}")
        except Exception as e:
            self.logger.error(f"Failed to create operator instance: {e}", exc_info=True)
            raise
                # Create emit context for mixed environment


        try:
            self.operator.insert_emit_context(RayEmitContext())
            self.operator.insert_runtime_context(RuntimeContext(self.memory_collection, self.logger))
            self.logger.debug(f"Injected emit context for operator in node {self.name}")
        except Exception as e:
            self.logger.warning(f"Failed to inject emit context in node {self.name}: {e}")


        # Running state management
        self._running = False
        self._stop_requested = False
        self.logger.info(f"Created Ray actor node: {self.name}")

    def add_downstream_node(self,output_channel:int, broadcast_index:int,parallel_index:int, target_input_channel:int,   downstream_handle: Union[ActorHandle, str]):
        try:
            # 下游是Ray Actor
            self.operator.add_downstream_target(
                output_channel,
                broadcast_index,
                parallel_index,
                downstream_handle,
                target_input_channel
            )
            self.logger.debug(f"Added downstream target: {downstream_handle}[{output_channel}]")
                
        except Exception as e:
            self.logger.error(f"Error adding downstream node: {e}", exc_info=True)
            raise

    def receive(self, input_tag: str, data: Any):
        """
        Receive data from upstream node and process it.
        This method is called directly by upstream nodes (Ray actors or local nodes via TCP).
        
        Note: Ray platform automatically queues these method calls, so no input buffer needed.
        
        Args:
            input_channel: The input channel number on this node
            data: Data received from upstream
        """
        try:
            
            if self._stop_requested:
                self.logger.debug(f"Ignoring data on stopped node {self.name}")
                return
                
            self.logger.debug(f"Received data in node {self.name}, channel {input_tag}")
            
            # Call operator's receive method with correct input channel
            self.operator.process_data(input_tag, data)
            
        except Exception as e:
            self.logger.error(f"Error processing data in node {self.name}: {e}", exc_info=True)
            raise
    
    def run_once(self) -> None:
        if self.transformation.type != TransformationType.SOURCE:
            self.logger.warning(f"Node '{self.name}' is not a spout node, cannot run once.")
            return
        self.logger.info(f"Spout node '{self.name}' is running once.")
        self.operator.process_data(None, None)



    def run_loop(self): # deprecated
        """
        Start the node. For spout nodes, this starts the generation loop.
        For non-spout nodes, this just marks the node as ready to receive data.
        """
        self._running = True
        self._stop_requested = False
        
        if self.transformation.type == TransformationType.SOURCE:
            # Start spout execution asynchronously
            try:
                while self._running and not self._stop_requested:
                    # For spout nodes, call operator.receive with dummy channel and data
                    self.operator.process_data(None, None)
                    time.sleep(0.1)  # Small delay to prevent overwhelming
                    
            except Exception as e:
                self.logger.error(f"Error in spout node {self.name}: {e}", exc_info=True)
                raise
            finally:
                self._running = False
                self.logger.info(f"Spout execution stopped for node {self.name}")
        else:
            # For non-spout nodes, just mark as running

            self.logger.info(f"Ray node {self.name} started and ready to receive data")

    def stop(self):
        """Stop the node execution."""
        self._stop_requested = True
        self._running = False
        self.logger.info(f"Ray node {self.name} stopped")

    def is_running(self):
        """Check if the node is currently running."""
        return self._running and not self._stop_requested

    def get_name(self):
        """Get node name."""
        return self.name

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