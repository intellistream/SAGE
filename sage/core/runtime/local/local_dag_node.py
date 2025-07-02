from __future__ import annotations
import threading
import time
from typing import Any, Union, Tuple


#from sage.archive.operator_wrapper import OperatorWrapper
from sage.core.io.message_queue import MessageQueue
from sage.core.io.local_emit_context import LocalEmitContext
from sage.core.operator.transformation import Transformation, TransformationType
from sage_utils.custom_logger import CustomLogger
from ray.actor import ActorHandle


class LocalDAGNode:
    """
    Multiplexer DAG Node.

    This node can handle multiple upstream nodes and emit results to multiple downstream nodes.
    It is designed for scenarios where data from multiple sources needs to be processed together.
    """

    def __init__(self, 
                 name:str,
                 transformation:Transformation) -> None:
        """
        Initialize the multiplexer DAG node.
# 
        Args:
            name: Unique name of the node
            operator: An operator implementing the execution logic
            config: Optional dictionary of configuration parameters for the operator
            is_spout: Indicates if the node is the spout (starting point)
        """
        self.name = name
        self.transformation = transformation
        self.operator = transformation.build_instance()
        self.operator.insert_emit_context(LocalEmitContext())


        self.is_spout = transformation.transformation_type == TransformationType.SOURCE  # Check if this is a spout node 正确
        
        self.input_buffer = MessageQueue()  # Local input buffer for this node

        # Initialize stop event
        self.stop_event = threading.Event()

        self._current_channel_index = 0
        self._initialized = False


        self.logger = CustomLogger(
            object_name=f"LocalDAGNode_{self.name}",
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )
        # self.logger.info(f"transformation_type: {transformation.transformation_type}")
        self.logger.info(f"Initialized LocalDAGNode: {self.name} (spout: {self.is_spout})")

    
    def put(self, data_packet: Tuple[int, Any]):
        """
        向输入缓冲区放入数据包
        
        Args:
            data_packet: (input_channel, data) 元组
        """
        self.input_buffer.put(data_packet, timeout=1.0)
        self.logger.debug(f"Put data packet into buffer: channel={data_packet[0]}")

    def add_downstream_node(self,output_channel:int, target_input_channel:int,   downstream_handle: Union[ActorHandle, str]):
        try:
            # 下游是Ray Actor
            self.operator.add_downstream_target(
                output_channel=output_channel,
                target_object=downstream_handle,
                target_input_channel=target_input_channel
            )
            self.logger.debug(f"Added downstream target: {downstream_handle}[{output_channel}]")
                
        except Exception as e:
            self.logger.error(f"Error adding downstream node: {e}", exc_info=True)
            raise
    
    def run_loop(self) -> None:
        """
        Main worker loop that executes continuously until stop is signaled.
        """

        # Ensure all runtime objects are initialized
        self.stop_event.clear()

        # Main execution loop
        while not self.stop_event.is_set():
            try:
                if self.is_spout:
                    # For spout nodes, call operator.receive with dummy channel and data
                    self.operator.receive(0, None)
                    time.sleep(1)  # Sleep to avoid busy loop
                else:
                    # For non-spout nodes, fetch input and process
                    # input_result = self.fetch_input()
                    data_packet = self.input_buffer.get(timeout=0.5)
                    if(data_packet is None):
                        time.sleep(0.1)  # Short sleep when no data to process
                        continue
                    (input_channel, data) = data_packet
                    self.logger.debug(f"Processing data from buffer: channel={input_channel}")
                    # Call operator's receive method with the channel_id and data
                    self.operator.receive(input_channel, data)
                    
            except Exception as e:
                self.logger.error(
                    f"Critical error in node '{self.name}': {str(e)}",
                    exc_info=True
                )
                self.stop()
                raise RuntimeError(f"Execution failed in node '{self.name}'")

    def stop(self) -> None:
        """Signal the worker loop to stop."""
        if hasattr(self, 'stop_event') and self.stop_event and not self.stop_event.is_set():
            self.stop_event.set()
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(f"Node '{self.name}' received stop signal.")


    def __getstate__(self):
        """
        Custom serialization to exclude non-serializable objects.
        """
        state = self.__dict__.copy()
        # Remove non-serializable objects
        state.pop('logger', None)
        state.pop('stop_event', None)
        return state

    def __setstate__(self, state):
        """
        Custom deserialization to restore state.
        """
        self.__dict__.update(state)
        # Mark as not initialized so runtime objects will be created when needed
        self._initialized = False


