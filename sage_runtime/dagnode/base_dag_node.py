from abc import ABC, abstractmethod
import threading
from typing import Any, TYPE_CHECKING, Union
from sage_utils.custom_logger import CustomLogger
from sage_runtime.runtime_context import RuntimeContext
from ray.actor import ActorHandle

if TYPE_CHECKING:
    from sage_runtime.io.connection import Connection
    from sage_core.core.operator.base_operator import BaseOperator
    from sage_core.api.transformation import Transformation, OperatorFactory
    from sage_core.core.compiler import Compiler, GraphNode

class BaseDAGNode(ABC):
    def __init__(
        self, 
        name:str, 
        operator_factory: 'OperatorFactory',
        parallel_index: int = 0,
        parallelism: int = 1,
        delay: float = 0.1,
        memory_collection:Union[ActorHandle, Any] = None, 
        remote:bool = False,
        env_name:str = None,
        is_spout:bool = False
    ) -> None:
        self.operator_factory: 'OperatorFactory' = operator_factory
        self.delay = delay
        self.name = name
        self.is_spout = is_spout  # Check if this is a spout node

        # Create logger first
        self.logger = CustomLogger(
            filename=f"Node_{self.name}",
            env_name=env_name,
            console_output="WARNING",
            file_output="DEBUG",
            global_output = "WARNING",
            name = f"{self.name}_{self.__class__.__name__}"
        )
        

        self.operator:BaseOperator = operator_factory.create_operator(name = self.name)
        self.memory_collection = memory_collection  # Optional memory collection for this node
        self._running = False
        # Initialize stop event
        self.stop_event = threading.Event()

        pass
    
    @abstractmethod
    def run_loop(self) -> None:
        """
        Run the node's processing loop.
        This method should be implemented by subclasses to define the node's behavior.
        """
        pass 

    def add_connection(self, connection: 'Connection'):
        """
        添加连接到DAG节点
        :param connection: Connection对象，包含连接信息
        """
        self.operator.add_connection(connection)
        self.logger.debug(f"Connection added to node '{self.name}': {connection}")

    def submit(self):
        pass


    def trigger(self, input_tag: str = None, data:Any = None) -> None:
        """
        Execute the node once, processing any available input data.
        This is typically used for spout nodes to emit initial data.
        """
        try:
            self.logger.debug(f"Received data in node {self.name}, channel {input_tag}")
            self.operator.receive_packet( data)
        except Exception as e:
            self.logger.error(f"Error processing data in node {self.name}: {e}", exc_info=True)
            raise


    def stop(self) -> None:
        """Signal the worker loop to stop."""
        if not self.stop_event.is_set():
            self.stop_event.set()
            self.logger.info(f"Node '{self.name}' received stop signal.")



    def is_running(self):
        """Check if the node is currently running."""
        return self._running