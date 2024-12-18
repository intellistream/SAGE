import logging
from src.core.query_engine.query_optimization.base_optimization import BaseOptimization


class NoOpOptimization(BaseOptimization):
    """
    A no-operation optimization strategy that returns the DAG as-is.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def apply(self, dag):
        """
        Return the DAG without making any changes.
        :param dag: The input DAG.
        :return: The unchanged DAG.
        """
        self.logger.info("Applying NoOpOptimization: Returning DAG as-is.")
        return dag
