from src.core.operators.base_operator import BaseOperator
class Embedder(BaseOperator):
    """
    Base class for all operators.
    Each operator should inherit this class and implement the `execute` method.
    """

    ##TODO: TONG JUN
    def execute(self, input_data, **kwargs):
        """
        Execute the operator with the provided input data.
        :param input_data: Data to process.
        :param kwargs: Additional parameters for the operator.
        :return: Processed output data.
        """
        raise NotImplementedError("Each operator must implement the `execute` method.")

