import logging
from src.core.query_engine.operators.base_operator import BaseOperator


class Spout(BaseOperator):
    """
    Spout operator for injecting user input into the DAG.
    This operator acts as the first node in the DAG, passing the initial input data downstream.
    """

    def __init__(self, input_data):
        """
        Initialize the Spout operator with input data.
        :param input_data: The data to emit downstream. TODO:<array>
        """
        super().__init__()
        self.input_data = input_data
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, input_data=None, **kwargs):
        """
        Emit the user-provided input data to downstream nodes.
        :param input_data: Not used for Spout, as it uses its own input_data.
        :param kwargs: Additional parameters (not used for Spout).
        :return: None
        """
        try:
            self.logger.info(f"Spout emitting data: {self.input_data}")
            self.emit(self.input_data)
        except Exception as e:
            self.logger.error(f"Error in Spout execution: {str(e)}")
            raise RuntimeError(f"Spout execution failed: {str(e)}")