import ray
import asyncio
import logging
import time
from typing import Any, List, Optional, Dict, Tuple, TYPE_CHECKING, Type, Union
from ray.actor import ActorHandle
from sage.api.operator.base_operator_api import BaseFunction
from sage.core.graph import GraphEdge, GraphNode
from sage.core.io.emit_context import NodeType
from sage.core.io.ray_emit_context import RayEmitContext
from sage.utils.custom_logger import CustomLogger
from sage.core.runtime.local.local_dag_node import LocalDAGNode
@ray.remote
class RayDAGNode:
    """
    Ray Actor version of LocalDAGNode for distributed execution.
    
    Unlike local nodes, Ray actors don't need input buffers as Ray platform
    maintains the request queue for actors automatically.
    """
    
    def __init__(self, 
                 name: str, 
                 function_class: Type[BaseFunction],
                 operator_config: Dict = None,
                 is_spout: bool = False,
                 session_folder: str = None) -> None:
        """
        Initialize Ray multiplexer DAG node.
        
        Args:
            name: Node name
            function_class: Operator class (not instance)
            operator_config: Configuration for operator instantiation
            is_spout: Whether this is a spout node
            session_folder: Session folder for logging
        """
        self.name = name
        self.function_class = function_class
        self.operator_config = operator_config or {}
        self.is_spout = is_spout
        self._initialized = False
        
        # Running state management
        self._running = False
        self._stop_requested = False
        
        # Create logger first
        self.logger = CustomLogger(
            object_name=f"RayNode_{self.name}",
            session_folder=session_folder,
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        
        # Create emit context for mixed environment
        self.emit_context = RayEmitContext(
            self.name, 
            ray_node_actor=self,
            session_folder=session_folder
        )
        self._emit_context_injected = False
        
        self.logger.info(f"Created Ray actor node: {self.name}")

    def _ensure_initialized(self):
        """
        Ensure that all runtime objects are initialized.
        Called when the node actually starts running.
        """
        if self._initialized:
            return
        
        # Create operator instance locally within the Ray actor
        operator_config = self.operator_config.copy()
        operator_config["session_folder"] = CustomLogger.get_session_folder()
        
        try:
            self.operator = self.function_class(operator_config)
            self.logger.debug(f"Created operator instance for {self.name}")
        except Exception as e:
            self.logger.error(f"Failed to create operator instance: {e}", exc_info=True)
            raise
        
        # Inject emit context if operator supports it
        if hasattr(self.operator, 'set_emit_context') and not self._emit_context_injected:
            try:
                self.operator.set_emit_context(self.emit_context)
                self._emit_context_injected = True
                self.logger.debug(f"Injected emit context for operator in node {self.name}")
            except Exception as e:
                self.logger.warning(f"Failed to inject emit context in node {self.name}: {e}")
        
        self._initialized = True

    def add_downstream_node(self,output_channel:int, target_input_channel:int,   downstream_handle: Union[ActorHandle, str]):
        """
        添加下游节点到emit context
        
        Args:
            output_edge: 输出边
            downstream_operator: 下游操作符（Ray Actor或本地节点）
        """
        try:
            if isinstance(downstream_handle, ActorHandle):
                # 下游是Ray Actor
                self.emit_context.add_downstream_target(
                    output_channel=output_channel,
                    node_type=NodeType.RAY_ACTOR,
                    target_object=downstream_handle,
                    target_input_channel=target_input_channel,
                    node_name=f"RayActor_output_channel_{output_channel}"
                )
                self.logger.debug(f"Added Ray actor downstream: {self.name}[{output_channel}]")
            
            else:
                # 下游是本地节点（通过TCP通信）
                self.emit_context.add_downstream_target(
                    output_channel=output_channel,
                    node_type=NodeType.LOCAL,
                    target_object=None,  # TCP通信不需要直接引用
                    target_input_channel=target_input_channel,
                    node_name=downstream_handle
                )
                self.logger.debug(f"Added local node downstream: {self.name}[{output_channel}] -> "
                                f"{downstream_handle}[{target_input_channel}] (via TCP)")
                
        except Exception as e:
            self.logger.error(f"Error adding downstream node: {e}", exc_info=True)
            raise

    def receive(self, input_channel: int, data: Any):
        """
        Receive data from upstream node and process it.
        This method is called directly by upstream nodes (Ray actors or local nodes via TCP).
        
        Note: Ray platform automatically queues these method calls, so no input buffer needed.
        
        Args:
            input_channel: The input channel number on this node
            data: Data received from upstream
        """
        try:
            # Ensure initialization on first call
            self._ensure_initialized()
            
            if self._stop_requested:
                self.logger.debug(f"Ignoring data on stopped node {self.name}")
                return
                
            self.logger.debug(f"Received data in node {self.name}, channel {input_channel}")
            
            # Call operator's receive method with correct input channel
            self.operator.receive(input_channel, data)
            
        except Exception as e:
            self.logger.error(f"Error processing data in node {self.name}: {e}", exc_info=True)
            raise

    # 理论上来说，emit方法不会被调用，因为算子会直接调用emit_context.emit
    # 但为了兼容性和未来可能的需求，这里保留emit方法
    def emit(self, output_channel: int, data: Any):
        """
        Emit data to downstream nodes through the specified output channel.
        Called by the operator through emit context.
        
        Args:
            output_channel: This node's output channel number (-1 for all channels)
            data: Data to emit
        """
        try:
            self.emit_context.emit(output_channel, data)
        except Exception as e:
            self.logger.error(f"Error emitting data from {self.name}[out:{output_channel}]: {e}", exc_info=True)
            raise

    def start_spout(self):
        """
        Start the spout node execution.
        For spout nodes, continuously call operator.receive with dummy data.
        This runs in a loop until stop is requested.
        """
        if not self.is_spout:
            self.logger.warning(f"start_spout called on non-spout node {self.name}")
            return
        
        # Ensure initialization
        self._ensure_initialized()
            
        self._running = True
        self._stop_requested = False
        
        self.logger.info(f"Starting spout execution for node {self.name}")
        
        try:
            while self._running and not self._stop_requested:
                # For spout nodes, call operator.receive with dummy channel and data
                self.operator.receive(0, None)
                time.sleep(0.1)  # Small delay to prevent overwhelming
                
        except Exception as e:
            self.logger.error(f"Error in spout node {self.name}: {e}", exc_info=True)
            raise
        finally:
            self._running = False
            self.logger.info(f"Spout execution stopped for node {self.name}")

    def start(self):
        """
        Start the node. For spout nodes, this starts the generation loop.
        For non-spout nodes, this just marks the node as ready to receive data.
        """
        self._ensure_initialized()
        
        if self.is_spout:
            # Start spout execution asynchronously
            self.start_spout()
        else:
            # For non-spout nodes, just mark as running
            self._running = True
            self._stop_requested = False
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
        # Mark as not initialized so runtime objects will be created when needed
        self._initialized = False