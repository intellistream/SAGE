import ray
import asyncio
import logging
from typing import Any, List, Optional, Dict, Tuple, TYPE_CHECKING, Type
# from sage.archive.operator_wrapper import OperatorWrapper
from sage.api.operator.base_operator_api import BaseFuction
from sage.api.operator.base_operator_api import EmitContext
from sage.utils.custom_logger import CustomLogger
from ray.actor import ActorHandle  # 只在类型检查期间生效
import time
@ray.remote
class RayMultiplexerDagNode:
    """
    Ray Actor version of MultiplexerDagNode for distributed execution.
    """
    
    def __init__(self, 
                 name: str, 
                 operator_class: Type[BaseFuction],
                 operator_config: Dict = None,
                 is_spout: bool = False,
                 session_folder: str = None) -> None:
        self.name = name
        self.operator_class = operator_class
        self.operator_config = operator_config or {}
        self.is_spout = is_spout

        self.logger = CustomLogger(
            object_name=f"RayNode_{self.name}",
            session_folder=session_folder,
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )

        # 取消继承 root logger 的 stdout handler
        # self.logger.propagate = False
        """
        Initialize Ray multiplexer DAG node.
        
        Args:
            name: Node name
            operator_class: Operator class (not instance)
            operator_config: Configuration for operator instantiation
            is_spout: Whether this is a spout node
        """

        
        # Create operator instance locally within the Ray actor
      

        # Store downstream connections: output_channel -> [(downstream_actor, downstream_input_channel)]
        self.downstream_connections: List[Tuple[ActorHandle, int]] = []

        operator_config["session_folder"] = session_folder
        self.operator = operator_class(operator_config)
        
        # Running state
        self._running = False
        self._stop_requested = False
        
        # Create emit context for Ray environment
        self.emit_context = RayEmitContext(self.name, self)
        
        # Inject emit context if operator supports it
        if hasattr(self.operator, 'set_emit_context'):
            try:
                self.operator.set_emit_context(self.emit_context)
            except Exception as e:
                pass


    def add_downstream_connection(self, output_channel: int, downstream_actor:ActorHandle, 
                                downstream_input_channel: int):
        """
        Add downstream connection mapping.
        
        Args:
            output_channel: This node's output channel number
            downstream_actor: Downstream Ray actor handle
            downstream_input_channel: Downstream node's input channel number
        """
        if output_channel >= len(self.downstream_connections):
            self.downstream_connections.extend([None] * (output_channel + 1 - len(self.downstream_connections)))
        if self.downstream_connections[output_channel] is not None:
            raise ValueError(
                f"Output channel {output_channel} already has a downstream connection in node {self.name}"
            )
        
        self.downstream_connections[output_channel] = (downstream_actor, downstream_input_channel)
        
        self.logger.debug(
            f"Added downstream connection: {self.name}[out:{output_channel}] -> "
            f"downstream_node[in:{downstream_input_channel}]"
        )
    
    def receive(self, input_channel: int, data: Any):
        """
        Receive data from upstream node and process it.
        This method is called directly by upstream Ray actors.
        
        Args:
            input_channel: The input channel number on this node
            data: Data received from upstream
        """
        try:
            if self._stop_requested:
                return
                
            # Call operator's receive method with correct input channel
            self.logger.debug(f"Received data in node {self.name}, channel {input_channel}")
            self.operator.receive(input_channel, data)
            
        except Exception as e:
            self.logger.error(f"Error processing data in node {self.name}: {e}", exc_info=True)
            raise
    
    def emit(self, output_channel: int, data: Any):
        """
        Emit data to downstream actors through the specified output channel.
        Called by the operator through emit context.
        
        Args:
            output_channel: This node's output channel number (-1 for all channels)
            data: Data to emit
        """
        if output_channel == -1:
            # Special case for broadcasting to all channels
            for downstream_actor, downstream_input_channel in self.downstream_connections:
                if downstream_actor is not None:  # Skip None entries
                    try:
                        # Asynchronously call downstream actor's receive method
                        downstream_actor.receive.remote(downstream_input_channel, data)
                        
                        self.logger.debug(
                            f"Emitted data from {self.name}[out:all] to "
                            f"downstream[in:{downstream_input_channel}]"
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to emit data from {self.name}[out:all]: {e}"
                        )
        elif 0 <= output_channel < len(self.downstream_connections):
            connection = self.downstream_connections[output_channel]
            if connection is not None:
                downstream_actor, downstream_input_channel = connection
                try:
                    # Asynchronously call downstream actor's receive method
                    downstream_actor.receive.remote(downstream_input_channel, data)
                    
                    self.logger.debug(
                        f"Emitted data from {self.name}[out:{output_channel}] to "
                        f"downstream[in:{downstream_input_channel}]"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to emit data from {self.name}[out:{output_channel}]: {e}"
                    )
            else:
                self.logger.warning(
                    f"No downstream connection for output channel {output_channel} in node {self.name}"
                )
        else:
            self.logger.warning(
                f"Invalid output channel {output_channel} in node {self.name}"
            )
    
    def get_downstream_connections(self) -> List[Tuple[ActorHandle, int]]:
        """Get all downstream connections for debugging."""
        return self.downstream_connections.copy()
    
    def start_spout(self):
        """
        Start the spout node execution.
        For spout nodes, continuously call operator.receive with dummy data.
        """
        if not self.is_spout:
            self.logger.warning(f"start_spout called on non-spout node {self.name}")
            return
            
        self._running = True
        self._stop_requested = False
        
        try:
            while self._running and not self._stop_requested:
                # For spout, we typically call with channel 0 and None data
                self.operator.receive(0, None)
                time.sleep(1)
        except Exception as e:
            self.logger.error(f"Error in spout node {self.name}: {e}", exc_info=True)
            raise
        finally:
            self._running = False
    
    def stop(self):
        """Stop the node execution."""
        self._stop_requested = True
        self._running = False
        # self.logger.info(f"Ray node {self.name} stopped")
    
    def is_running(self):
        """Check if the node is currently running."""
        return self._running
    
    def get_name(self):
        """Get node name."""
        return self.name


class RayEmitContext(EmitContext):
    """
    Ray-specific emit context that uses direct actor calls instead of message queues.
    """
    
    def __init__(self, node_name: str, ray_node_actor):
        super().__init__(node_name)
        self.ray_node_actor = ray_node_actor
    
    def emit(self, channel: int, data: Any):
        """Emit data through Ray actor's emit method."""
        self.ray_node_actor.emit(channel, data)
    
    def add_downstream_channel(self, channel):
        """For Ray actors, downstream channels are managed differently."""
        pass  # No-op for Ray implementation