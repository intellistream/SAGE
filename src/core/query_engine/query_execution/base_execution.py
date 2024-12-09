from abc import ABC, abstractmethod

class ExecutionStrategy(ABC):
    """
    Base class for execution strategies.
    """

    @abstractmethod
    def execute(self, dag):
        """
        Execute the DAG.
        :param dag: The DAG to execute.
        :return: Results of execution.
        """
        pass
