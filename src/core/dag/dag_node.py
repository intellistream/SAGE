from queue import Queue
import logging


class DAGNode:
    """
    Represents an individual node in a DAG.
    Each node encapsulates an operator and manages execution with message passing.
    """

    def __init__(self, name, operator, config=None, is_spout=False):
        """
        Initialize the DAG node.
        :param name: Unique name of the node.
        :param operator: An operator implementing the execution logic.
        :param config: Optional dictionary of configuration parameters for the operator.
        :param is_spout: Indicates if the node is the spout (starting point).
        """
        self.name = name
        self.operator = operator
        self.config = config or {}
        self.is_spout = is_spout
        self.logger = logging.getLogger(__name__)
        self.output_queue = Queue()
        self.upstream_nodes = []  # List of upstream DAGNodes
        self.downstream_nodes = []  # List of downstream DAGNodes

    def add_upstream_node(self, node):
        """
        Add an upstream node. This node fetches input from the upstream node's output queue.
        :param node: A DAGNode instance.
        """
        if node not in self.upstream_nodes:
            self.upstream_nodes.append(node)
            self.logger.info(f"Node '{self.name}' connected to upstream node '{node.name}'.")

    def add_downstream_node(self, node):
        """
        Add a downstream node. The downstream node uses this node's output queue as its input source.
        :param node: A DAGNode instance.
        """
        if node not in self.downstream_nodes:
            self.downstream_nodes.append(node)
            node.add_upstream_node(self)
            self.logger.info(f"Node '{self.name}' connected to downstream node '{node.name}'.")

    def execute(self):
        """
        Fetch input from upstream nodes, execute the operator logic, and deliver output to the output queue.
        """
        self.logger.info(f"Node '{self.name}' starting execution.")
        try:
            # Fetch input if not a spout
            input_data = None if self.is_spout else self._fetch_input()
            if input_data is None and not self.is_spout:
                self.logger.warning(f"Node '{self.name}' has no input to process.")
                return

            # Execute the operator logic
            self.operator.output_queue = self.output_queue  # Set operator's output queue
            self.operator.execute(input_data, **self.config)

        except Exception as e:
            self.logger.error(f"Error in node '{self.name}': {str(e)}")
            raise RuntimeError(f"Execution failed in node '{self.name}': {str(e)}")

    def _fetch_input(self):
        """
        Fetch input from upstream nodes' output queues.
        :return: Aggregated input data from upstream nodes or None if no data is available.
        """
        aggregated_input = []
        for upstream_node in self.upstream_nodes:
            while not upstream_node.output_queue.empty():
                aggregated_input.append(upstream_node.output_queue.get())

        return aggregated_input if aggregated_input else None

    def __repr__(self):
        return f"DAGNode(name={self.name}, operator={self.operator.__class__.__name__})"
