import logging


class BaseOptimization:
    """
    Base class for DAG optimization strategies.
    Provides a template for custom optimization methods.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def apply(self, dag):
        """
        Apply the optimization strategy to the DAG.
        Subclasses must override this method.
        :param dag: The input DAG to optimize.
        :return: Optimized DAG.
        """
        raise NotImplementedError("Subclasses must implement the `apply` method.")
