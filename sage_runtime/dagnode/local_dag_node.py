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


    
    def runtime_init(self, runtime_context: 'RuntimeContext') -> None:
        """
        Initialize the runtime context and other parameters.
        """
        try:
            self.runtime_context = runtime_context
            self.logger = CustomLogger(
                filename=f"Node_{runtime_context.name}",
                env_name=runtime_context.env_name,
                console_output="WARNING",
                file_output="DEBUG",
                global_output = "WARNING",
                name = f"{runtime_context.name}_{self.__class__.__name__}"
            )
            self.operator = self.operator_factory.create_operator(name=self.name)
            self.operator.runtime_init(runtime_context)
            # Create logger first

            self.input_buffer = LocalMessageQueue(name = self.name, env_name=runtime_context.env_name)  # Local input buffer for this node

            # self.logger.info(f"type: {transformation.type}")
            self.logger.info(f"Initialized LocalDAGNode: {self.name} (spout: {self.is_spout})")
        except Exception as e:
            self.logger.error(f"Failed to initialize node {self.name}: {e}", exc_info=True)
    
    def put(self, data_packet: Any):
        """
        向输入缓冲区放入数据包
        
        Args:
            data_packet: (input_channel, data) 元组
        """
        self.input_buffer.put(data_packet, timeout=1.0)
        self.logger.debug(f"Put data packet into buffer")
    

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
                    self.logger.debug(f"Running spout node '{self.name}'")
                    # For spout nodes, call operator.receive with dummy channel and data
                    self.operator.receive_packet(None)
                    time.sleep(self.delay)  # Sleep to avoid busy loop
                else:
                    # For non-spout nodes, fetch input and process
                    # input_result = self.fetch_input()
                    data_packet = self.input_buffer.get(timeout=0.5)
                    if(data_packet is None):
                        time.sleep(0.1)  # Short sleep when no data to process
                        continue
                    # Call operator's receive method with the channel_id and data
                    self.operator.receive_packet(data_packet)
            except Exception as e:
                self.logger.error(
                    f"Critical error in node '{self.name}': {str(e)}",
                    exc_info=True
                )
                self.stop()
                raise RuntimeError(f"Execution failed in node '{self.name}'")
            finally:
                self._running = False