from queue import Queue, Empty
import logging
import threading
import time


class BaseDAGNode:
    """
    Base class for DAG nodes, defining shared functionality for all node types.
    """

    def __init__(self, name, operator, config=None, is_spout=False):
        """
        Initialize the base DAG node.
        :param name: Unique name of the node.
        :param operator: An operator implementing the execution logic.
        :param config: Optional dictionary of configuration parameters for the operator.
        :param is_spout: Indicates if the node is the spout (starting point).
        """
        self.name = name
        self.operator = operator
        self.config = config or {}
        self.is_spout = is_spout
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_queue = Queue()
        self.upstream_nodes = []  # List of upstream DAGNodes
        self.downstream_nodes = []  # List of downstream DAGNodes
        self.is_executed = False

    def add_upstream_node(self, node):
        """
        Add an upstream node. This node fetches input from the upstream node's output queue.
        :param node: A BaseDAGNode instance.
        """
        if node not in self.upstream_nodes:
            self.upstream_nodes.append(node)
            self.logger.info(f"Node '{self.name}' connected to upstream node '{node.name}'.")

    def add_downstream_node(self, node):
        """
        Add a downstream node. The downstream node uses this node's output queue as its input source.
        :param node: A BaseDAGNode instance.
        """
        if node not in self.downstream_nodes:
            self.downstream_nodes.append(node)
            node.add_upstream_node(self)
            self.logger.info(f"Node '{self.name}' connected to downstream node '{node.name}'.")

    def fetch_input(self):
        """
        Fetch input from upstream nodes' output queues.
        :return: Aggregated input data from upstream nodes or None if no data is available.
        """
        aggregated_input = []
        for upstream_node in self.upstream_nodes:
            while not upstream_node.output_queue.empty():
                aggregated_input.append(upstream_node.output_queue.get())
        return aggregated_input if aggregated_input else None

    def execute(self):
        """
        This method must be implemented by subclasses to define specific execution behavior.
        """
        raise NotImplementedError("Subclasses must implement the `execute` method.")
