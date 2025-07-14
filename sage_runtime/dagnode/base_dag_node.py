from abc import ABC, abstractmethod
import threading, copy
from typing import Any, TYPE_CHECKING, Union
from sage_utils.custom_logger import CustomLogger
from sage_runtime.runtime_context import RuntimeContext
from ray.actor import ActorHandle

if TYPE_CHECKING:
    from sage_runtime.io.connection import Connection
    from sage_core.operator.base_operator import BaseOperator
    from sage_core.transformation.base_transformation import BaseTransformation, OperatorFactory
    from sage_runtime.compiler import Compiler, GraphNode

class BaseDAGNode(ABC):
    def __init__(
        self, 
        name:str, 
        operator_factory: 'OperatorFactory',
    ) -> None:
        self.runtime_context: RuntimeContext
        self.operator:BaseOperator
        self.delay: Union[int, float] = 1
        self.is_spout: bool = False


        self.operator_factory: 'OperatorFactory' = operator_factory
        self.name = name
        self._running = False
        self.stop_event = threading.Event()

        pass

    def runtime_init(self, runtime_context: RuntimeContext) -> None:
        """
        Initialize the runtime context and other parameters.
        """
        try:
            self.runtime_context = runtime_context

            self.operator = self.operator_factory.create_operator(name=self.name)
            self.operator.runtime_init(copy.deepcopy(runtime_context))
            # Create logger first
            self.logger = CustomLogger(
                filename=f"Node_{runtime_context.name}",
                env_name=runtime_context.env_name,
                console_output="WARNING",
                file_output="DEBUG",
                global_output = "WARNING",
                name = f"{runtime_context.name}_{self.__class__.__name__}"
            )
            self.logger.info(f"Node {self.name} initialized with type {self.__class__.__name__}")
        except Exception as e:
            self.logger.error(f"Failed to initialize node {self.name}: {e}", exc_info=True)

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