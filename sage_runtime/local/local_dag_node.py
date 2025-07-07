from __future__ import annotations
import threading
import time
from typing import Any, Union, Tuple
from sage_core.core.operator.transformation import Transformation, TransformationType
from sage_runtime.io.local_emit_context import LocalEmitContext
from sage_runtime.io.local_message_queue import LocalMessageQueue
from sage_utils.custom_logger import CustomLogger
from ray.actor import ActorHandle
from sage_memory.memory_collection.base_collection import BaseMemoryCollection
from sage_runtime.runtime_context import RuntimeContext

class LocalDAGNode:
    """
    Multiplexer DAG Node.

    This node can handle multiple upstream nodes and emit results to multiple downstream nodes.
    It is designed for scenarios where data from multiple sources needs to be processed together.
    """

    def __init__(self, 
                 name:str,
                 transformation:Transformation, 
                 memory_collection:Union[BaseMemoryCollection, ActorHandle] = None
                 ) -> None:
        """
        Initialize the multiplexer DAG node.
# 
        Args:
            name: Unique name of the node
            operator: An operator implementing the execution logic
            config: Optional dictionary of configuration parameters for the operator
            is_spout: Indicates if the node is the spout (starting point)
        """
        self.logger = CustomLogger(
            object_name=f"LocalDAGNode_{name}",
            console_output=False,
            file_output=True
        )
        self.name = name
        self.transformation = transformation
        self.memory_collection = memory_collection  # Optional memory collection for this node
        self.operator = transformation.build_instance()
        self.operator.insert_emit_context(LocalEmitContext())
        self.operator.insert_runtime_context(RuntimeContext(self.memory_collection, logger=self.logger))



        self.is_spout = (transformation.type == TransformationType.SOURCE)  # Check if this is a spout node 正确
        self.input_buffer = LocalMessageQueue()  # Local input buffer for this node

        # Initialize stop event
        self.stop_event = threading.Event()



        # self.logger.info(f"type: {transformation.type}")
        self.logger.info(f"Initialized LocalDAGNode: {self.name} (spout: {self.is_spout}), config:{(transformation.kwargs).get('config', None)}")

    
    def put(self, data_packet: Tuple[int, Any]):
        """
        向输入缓冲区放入数据包
        
        Args:
            data_packet: (input_channel, data) 元组
        """
        self.input_buffer.put(data_packet, timeout=1.0)
        self.logger.debug(f"Put data packet into buffer: channel={data_packet[0]}")

    def add_downstream_node(self,output_tag:str, broadcast_index:int,parallel_index:int, downstream_input_tag:str,   downstream_handle: Union[ActorHandle, LocalDAGNode]):
        # broadcast_index:属于某个广播组
        # parallel_index:广播组内部的编号
        try:
            # 下游是Ray Actor
            self.operator.add_downstream_target(
                output_tag,
                broadcast_index,
                parallel_index,
                downstream_handle,
                downstream_input_tag
            )
            self.logger.debug(f"Added downstream target: {downstream_handle}in[{output_tag}]")
                
        except Exception as e:
            self.logger.error(f"Error adding downstream node: {e}", exc_info=True)
            raise
    
    def run_once(self) -> None:
        """
        Execute the node once, processing any available input data.
        This is typically used for spout nodes to emit initial data.
        """
        if self.is_spout is False:
            self.logger.warning(f"Node '{self.name}' is not a spout node, cannot run once.")
            return
        
        self.logger.info(f"Spout node '{self.name}' is running once.")
        self.operator.process_data(None, None)

    def run_loop(self) -> None:
        """
        Main worker loop that executes continuously until stop is signaled.
        """

        # Ensure all sage_runtime objects are initialized
        self.stop_event.clear()

        # Main execution loop
        while not self.stop_event.is_set():
            try:
                if self.is_spout:
                    # For spout nodes, call operator.receive with dummy channel and data
                    self.operator.process_data(None, None)
                    time.sleep(1)  # Sleep to avoid busy loop
                else:
                    # For non-spout nodes, fetch input and process
                    # input_result = self.fetch_input()
                    data_packet = self.input_buffer.get(timeout=0.5)
                    if(data_packet is None):
                        time.sleep(0.1)  # Short sleep when no data to process
                        continue
                    (input_tag, data) = data_packet
                    self.logger.debug(f"Processing data from buffer: tag={input_tag}")
                    # Call operator's receive method with the channel_id and data
                    self.operator.process_data(input_tag, data)
                    
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
        # Mark as not initialized so sage_runtime objects will be created when needed
        self._initialized = False


