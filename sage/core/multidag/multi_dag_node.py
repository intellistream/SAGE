import asyncio
import inspect
import logging
import threading
import time
from typing import Any, Type, TYPE_CHECKING, Union, List, Optional, Tuple


#from sage.archive.operator_wrapper import OperatorWrapper
from sage.api.operator.base_operator_api import BaseOperator
from sage.core.io.message_queue import MessageQueue
from sage.api.operator.base_operator_api import EmitContext

class MultiplexerDagNode:
    """
    Multiplexer DAG Node.

    This node can handle multiple upstream nodes and emit results to multiple downstream nodes.
    It is designed for scenarios where data from multiple sources needs to be processed together.
    """

    def __init__(self, 
                 name: str, 
                 operator: BaseOperator,
                 config: dict = None, 
                 is_spout: bool = False) -> None:
        """
        Initialize the multiplexer DAG node.

        Args:
            name: Unique name of the node
            operator: An operator implementing the execution logic
            config: Optional dictionary of configuration parameters for the operator
            is_spout: Indicates if the node is the spout (starting point)
        """
        self.name = name
        self.operator = operator
        self.config = config
        self.is_spout = is_spout
        # self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger = None
        self.upstream_channels: List[MessageQueue] = []
        self.downstream_channels: List[MessageQueue] = []
        # self.stop_event = threading.Event()
        # self.stop_event = None
        # self.operator.set_emit_func(self._create_emit_func())
        # Round-robin scheduling for upstream channels
        self._current_channel_index = 0
        self._initialized = False
        # Create emit context
        self.emit_context = EmitContext(self.name)
        # Don't inject emit context in __init__ to avoid serialization issues
        self._emit_context_injected = False
    def _ensure_initialized(self):
        """
        Ensure that all runtime objects are initialized.
        Called when the node actually starts running.
        """
        if self._initialized:
            return
            
        # Initialize logger
        self._logger = logging.getLogger(f"{self.__class__.__name__}.{self.name}")
        
        # Initialize stop event
        self._stop_event = threading.Event()
        
        # Inject emit context
        if hasattr(self.operator, 'set_emit_context') and not self._emit_context_injected:
            try:
                self.operator.set_emit_context(self.emit_context)
                self._emit_context_injected = True
                self._logger.debug(f"Injected emit context for operator in node {self.name}")
            except Exception as e:
                self._logger.warning(f"Failed to inject emit context in node {self.name}: {e}")
        
        self._initialized = True

    @property
    def logger(self):
        """Get logger, initializing if necessary."""
        if not hasattr(self, '_logger') or self._logger is None:
            self._ensure_initialized()
        return self._logger

    @property
    def stop_event(self):
        """Get stop event, initializing if necessary."""
        if not hasattr(self, '_stop_event') or self._stop_event is None:
            self._ensure_initialized()
        return self._stop_event
    


    def fetch_input(self) -> Optional[Tuple[int, Any]]:
        """
        Fetch input from upstream channels using round-robin scheduling.
        Returns a tuple of (channel_id, data) from the next available upstream channel.
        
        Returns:
            Tuple of (channel_id, data) or None if no data is available from any channel
        """
        if not self.upstream_channels:
            return None
        
        num_channels = len(self.upstream_channels)
        # Try all channels starting from current position
        for _ in range(num_channels):
            channel_id = self._current_channel_index
            channel:MessageQueue = self.upstream_channels[channel_id]
            
            # Move to next channel for next call (round-robin)
            self._current_channel_index = (self._current_channel_index + 1) % num_channels
            
            # Check if current channel has data
            if not channel.is_empty():
                data = channel.get()
                return (channel_id, data)
        
        # No data available from any channel
        return None
    



    def emit(self, channel: int, data: Any) -> None:
        """
        Emit data to specified downstream channel.
        
        Args:
            channel: The downstream channel index
            data: Data to emit
        """
        if channel < len(self.downstream_channels):
            self.downstream_channels[channel].put(data)
        else:
            self.logger.warning(f"Channel index {channel} out of range for node {self.name}")

    def add_downstream_channel(self, message_queue: MessageQueue):
        """Add downstream channel to both node and emit context."""
        self.downstream_channels.append(message_queue)
        self.emit_context.add_downstream_channel(message_queue)
    

    def _inject_emit_context_if_needed(self):
        """
        Inject emit context if not already done and if supported by operator.
        This is called at runtime to avoid serialization issues.
        """
        if not self._emit_context_injected and hasattr(self.operator, 'set_emit_context'):
            try:
                self.operator.set_emit_context(self.emit_context)
                self._emit_context_injected = True
                self.logger.debug(f"Injected emit context for operator in node {self.name}")
            except Exception as e:
                self.logger.warning(f"Failed to inject emit context in node {self.name}: {e}")

    def run_loop(self) -> None:
        """
        Main worker loop that executes continuously until stop is signaled.
        """

        # Ensure all runtime objects are initialized
        self._ensure_initialized()
        self.stop_event.clear()

        # Main execution loop
        while not self.stop_event.is_set():
            try:
                if self.is_spout:
                    # For spout nodes, call operator.receive with dummy channel and data
                    self.operator.receive(0, None)
                else:
                    # For non-spout nodes, fetch input and process
                    input_result = self.fetch_input()
                    if input_result is None:
                        time.sleep(0.1)  # Short sleep when no data to process
                        continue
                    
                    # Unpack the tuple: (channel_id, data)
                    channel_id, data = input_result
                    
                    # Call operator's receive method with the channel_id and data
                    self.operator.receive(channel_id, data)
                    
            except Exception as e:
                self.logger.error(
                    f"Critical error in node '{self.name}': {str(e)}",
                    exc_info=True
                )
                self.stop()
                raise RuntimeError(f"Execution failed in node '{self.name}'")

    def stop(self) -> None:
        """Signal the worker loop to stop."""
        if hasattr(self, '_stop_event') and self._stop_event and not self._stop_event.is_set():
            self._stop_event.set()
            if hasattr(self, '_logger') and self._logger:
                self._logger.info(f"Node '{self.name}' received stop signal.")


    def __getstate__(self):
        """
        Custom serialization to exclude non-serializable objects.
        """
        state = self.__dict__.copy()
        # Remove non-serializable objects
        state.pop('_logger', None)
        state.pop('_stop_event', None)
        return state

    def __setstate__(self, state):
        """
        Custom deserialization to restore state.
        """
        self.__dict__.update(state)
        # Mark as not initialized so runtime objects will be created when needed
        self._initialized = False


    # def add_upstream_channel(self, upstream_dagnode:MultiplexerDagNode,channel_index:int):
    #     """
    #     Add an upstream channel to this multiplexer node.
    #     目前只能顺序添加，不能随机添加。
    #     Args:
    #         upstream_dagnode: The upstream MultiplexerDagNode instance
    #         channel_index: The index of the channel in the upstream node
    #     """
    #     if channel_index < len(upstream_dagnode.downstream_channels):
    #         self.upstream_channels.append(upstream_dagnode.downstream_channels[channel_index])
    #     else:
    #         self.logger.error(f"Channel index {channel_index} out of range for upstream node {upstream_dagnode.name}.")


