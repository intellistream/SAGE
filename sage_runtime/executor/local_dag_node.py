from __future__ import annotations
import time
from typing import Any, Union, Tuple, TYPE_CHECKING
from sage_runtime.io.local_message_queue import LocalMessageQueue
from sage_runtime.runtime_context import RuntimeContext
from sage_runtime.executor.base_dag_node import BaseDagNode
from ray.actor import ActorHandle
from sage_memory.memory_collection.base_collection import BaseMemoryCollection
if TYPE_CHECKING:
    from sage_core.api.transformation import Transformation, OperatorFactory


class LocalDAGNode(BaseDagNode):
    """
    Multiplexer DAG Node.

    This node can handle multiple upstream nodes and emit results to multiple downstream nodes.
    It is designed for scenarios where data from multiple sources needs to be processed together.
    """

    def __init__(self, 
                 name:str,
                 operator_factory:'OperatorFactory', 
                 memory_collection:Union[BaseMemoryCollection, ActorHandle] = None
                 ) -> None:
        super().__init__(name, operator_factory)
        """
        Initialize the multiplexer DAG node.
# 
        Args:
            name: Unique name of the node
            operator: An operator implementing the execution logic
            config: Optional dictionary of configuration parameters for the operator
            is_spout: Indicates if the node is the spout (starting point)
        """
        self.memory_collection = memory_collection  # Optional memory collection for this node
        self.operator.insert_runtime_context(RuntimeContext(self.memory_collection, logger=self.logger))

        self.input_buffer = LocalMessageQueue(name = name)  # Local input buffer for this node

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
    

    def run_loop(self) -> None:
        """
        Main worker loop that executes continuously until stop is signaled.
        """

        # Ensure all sage_runtime objects are initialized
        self.stop_event.clear()
        self._running = True
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
            finally:
                self._running = False