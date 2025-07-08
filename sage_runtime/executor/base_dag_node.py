from abc import ABC, abstractmethod
import threading
from typing import Any, TYPE_CHECKING
from sage_utils.custom_logger import CustomLogger

if TYPE_CHECKING:
    from sage_runtime.io.connection import Connection
    from sage_core.core.operator.base_operator import BaseOperator
    from sage_core.api.transformation import Transformation, OperatorFactory

class BaseDagNode(ABC):
    def __init__(self, name, operator_factory:'OperatorFactory', session_folder=None):
        # Create logger first
        self.logger = CustomLogger(
            filename=f"{name}",
            session_folder=session_folder,
            console_output="WARNING",
            file_output="WARNING",
            global_output = "WARNING",
            name = f"{name}_{self.__class__.__name__}"
        )
        self.name = name
        self._running = False
        # Initialize stop event
        self.stop_event = threading.Event()

        self.is_spout = operator_factory.is_spout  # Check if this is a spout node 正确
        self.operator:'BaseOperator' = operator_factory.build_instance(session_folder=session_folder, name = name)
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


    def process(self, input_tag: str = None, data:Any = None) -> None:
        """
        Execute the node once, processing any available input data.
        This is typically used for spout nodes to emit initial data.
        """
        try:
            self.logger.debug(f"Received data in node {self.name}, channel {input_tag}")
            self.operator.process_data(input_tag, data)
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