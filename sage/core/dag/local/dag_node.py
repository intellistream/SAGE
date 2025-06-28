import asyncio
import inspect
import logging
import threading
import time
from typing import Any, Type, TYPE_CHECKING, Union


from sage.core.io.message_queue import MessageQueue
# from sage.archive.operator_wrapper import OperatorWrapper
# from sage.api.operator.base_operator_api import BaseOperator


class BaseDAGNode:
    """
    Base class for DAG nodes, defining shared functionality for all node types.

    Attributes:
        name (str): Unique name of the node
        operator (BaseOperator): Operator implementing the execution logic
        config (dict): Configuration parameters for the operator
        is_spout (bool): Indicates if the node is a spout (starting point)
        output_queue (MessageQueue): Output queue for the node's results
        upstream_nodes (list): List of upstream DAGNodes
        downstream_nodes (list): List of downstream DAGNodes
        is_executed (bool): Indicates if the node has been executed
        is_longrunning (bool): Indicates if the node is a long-running process
    """

    def __init__(self, name: str, operator,
                 config: dict = None, is_spout: bool = False) -> None:
        """
        Initialize the base DAG node.

        Args:
            name: Unique name of the node
            operator: An operator implementing the execution logic
            config: Optional dictionary of configuration parameters for the operator
            is_spout: Indicates if the node is the spout (starting point)
        """
        self.name = name
        self.operator = operator
        self.config = config or {}
        self.is_spout = is_spout
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_queue = MessageQueue()
        self.upstream_nodes = []  # List of upstream DAGNodes
        self.downstream_nodes = []  # List of downstream DAGNodes
        self.is_executed = False
        self.is_longrunning = False

    def add_upstream_node(self, node: 'BaseDAGNode') -> None:
        """
        Add an upstream node.

        This node fetches input from the upstream node's output queue.

        Args:
            node: A BaseDAGNode instance
        """
        if node not in self.upstream_nodes:
            self.upstream_nodes.append(node)

    def add_downstream_node(self, node: 'BaseDAGNode') -> None:
        """
        Add a downstream node.

        The downstream node uses this node's output queue as its input source.

        Args:
            node: A BaseDAGNode instance
        """
        if node not in self.downstream_nodes:
            self.downstream_nodes.append(node)
            node.add_upstream_node(self)

    def fetch_input(self) -> Any:
        """
        Fetch input from upstream nodes' output queues.

        Returns:
            Aggregated input data from upstream nodes or None if no data is available.
        """
        if not self.upstream_nodes:
            return None

        # TODO: Add Multi-Upstream support.
        # For multiple upstream nodes implementation:
        # aggregated_input = []
        # for upstream_node in self.upstream_nodes:
        #     while not upstream_node.output_queue.empty():
        #         aggregated_input.append(upstream_node.output_queue.get())
        #
        # return aggregated_input if aggregated_input else None

        # For single upstream implementation:
        return self.upstream_nodes[0].output_queue.get()

    def emit(self, output: Any) -> None:
        """
        Emit output to the output queue.

        Args:
            output: Data to be emitted
        """
        if output is not None:
            self.output_queue.put(output)

    def execute(self) -> None:
        """
        Execute the node logic.

        This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the `execute` method.")

    def get_name(self) -> str:
        """Return the node's name."""
        return self.name







class OneShotDAGNode(BaseDAGNode):
    """
    One-shot execution variant of DAGNode.
    Designed for execution that runs once and completes.
    """

    def execute(self) -> None:
        """
        Execute the operator logic once.

        If the node is a spout, it triggers its own execution.
        Otherwise, it processes input from upstream nodes.
        """
        try:
            if self.is_spout:
                ref = self.operator.execute()
                self.emit(ref)
            else:
                input_data = self.fetch_input()
                if input_data is None:
                    self.logger.warning(f"Node '{self.name}' has no input to process.")
                    return
                output = self.operator.execute(input_data)
                self.emit(output)

            self.is_executed = True
        except Exception as e:
            self.logger.error(f"Error in node '{self.name}': {str(e)}")
            raise RuntimeError(f"Execution failed in node '{self.name}': {str(e)}")


# class ContinuousDAGNode(BaseDAGNode):
#     """
#     Continuous execution variant of DAGNode.

#     Designed for nodes that need to run continuously until signaled to stop.

#     Attributes:
#         stop_event (threading.Event): Event to signal thread to stop
#         duration (int/float): Duration for which the node should run before stopping
#         _stop_timer (threading.Timer): Timer for scheduled stop
#     """

#     def __init__(self, name: str, operator: BaseOperator,
#                  config: dict = None, is_spout: bool = False) -> None:
#         """
#         Initialize the continuous DAG node.

#         Args:
#             name: Unique name of the node
#             operator: An operator implementing the execution logic
#             config: Optional dictionary of configuration parameters for the operator
#             is_spout: Indicates if the node is the spout (starting point)
#         """
#         super().__init__(name, operator, config, is_spout)
#         self.stop_event = threading.Event()

#         # Extract duration from config, default to None
#         self.duration = config.get("duration", None) if config else None
#         self._stop_timer = None

#     def run_loop(self) -> None:
#         """
#         Main worker loop that executes continuously until stop is signaled.

#         If a duration is specified, a timer is set to stop the loop automatically.
#         """
#         self.stop_event.clear()
#         # Set up stop timer if duration is specified
#         if self.duration is not None:
#             if not isinstance(self.duration, (int, float)) or self.duration <= 0:
#                 raise ValueError("duration must be a positive number")
#             self._stop_timer = threading.Timer(self.duration, self.stop)
#             self._stop_timer.start()

#         # Main execution loop
#         while not self.stop_event.is_set():
#             try:
#                 if self.is_spout:
#                     result = self.operator.execute()
#                     self.emit(result)
#                     if self.output_queue.qsize():
#                         print(f"{self.name} queue size is{self.output_queue.qsize()} ")
#                 else:
#                     input_data = self.fetch_input()
#                     if input_data is None:
#                         time.sleep(1)  # Short sleep when no data to process
#                         continue
#                     result = self.operator.execute(input_data)
#                     self.emit(result)
#                     if self.output_queue.qsize():
#                         print(f"{self.name} queue size is{self.output_queue.qsize()} ")
#             except Exception as e:
#                 self.logger.error(
#                     f"Critical error in node '{self.name}': {str(e)}",
#                     exc_info=True
#                 )
#                 self.stop()
#                 raise RuntimeError(f"Execution failed in node '{self.name}'")

#         # Clean up stop timer
#         if self._stop_timer and self._stop_timer.is_alive():
#             self._stop_timer.cancel()

#     def stop(self) -> None:
#         """Signal the worker loop to stop."""
#         if not self.stop_event.is_set():
#             self.stop_event.set()

#             # Cancel stop timer if active
#             if self._stop_timer and self._stop_timer.is_alive():
#                 self._stop_timer.cancel()

#             self.logger.info(f"Node '{self.name}' received stop signal.")


