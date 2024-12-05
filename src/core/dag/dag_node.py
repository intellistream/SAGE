import logging

class DAGNode:
    """
    Represents an individual node in a DAG.
    Each node encapsulates an operator and manages its execution logic.
    """

    def __init__(self, name, operator, config=None):
        """
        Initialize the DAG node.
        :param name: Unique name of the node.
        :param operator: Callable operator function or class implementing the logic.
        :param config: Optional dictionary of configuration parameters for the operator.
        """
        self.name = name
        self.operator = operator
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

    def execute(self, input_data):
        """
        Execute the operator encapsulated by the node.
        :param input_data: Input data for the operator.
        :return: Output data from the operator.
        """
        self.logger.info(f"Node '{self.name}' started execution with input: {input_data}")
        try:
            output_data = self.operator(input_data, **self.config)
            self.logger.info(f"Node '{self.name}' completed execution with output: {output_data}")
            return output_data
        except Exception as e:
            self.logger.error(f"Error in node '{self.name}': {str(e)}")
            raise RuntimeError(f"Execution failed in node '{self.name}': {str(e)}")

    def __repr__(self):
        """
        String representation of the DAG node.
        :return: String describing the node's name and operator.
        """
        return f"DAGNode(name={self.name}, operator={self.operator.__class__.__name__})"
