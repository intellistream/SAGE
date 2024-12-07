class BaseOperator:
    """
    Base class for all operators.
    Each operator should inherit this class and implement the `execute` method.
    """

    def __init__(self):
        """
        Initialize the operator with an empty output queue.
        """
        self.output_queue = None  # To be set by the DAGNode

    def emit(self, data):
        """
        Emit data to the output queue.
        This is called during execution to pass data downstream.
        :param data: Data to emit.
        """
        if self.output_queue is not None:
            self.output_queue.put(data)
        else:
            raise RuntimeError("Output queue is not set. Ensure this operator is part of a DAGNode.")

    def execute(self, input_data, **kwargs):
        """
        Execute the operator logic.
        Emit results during execution using `emit`.
        :param input_data: Data to process.
        :param kwargs: Additional parameters for the operator.
        :return: None
        """
        raise NotImplementedError("Each operator must implement the `execute` method.")
