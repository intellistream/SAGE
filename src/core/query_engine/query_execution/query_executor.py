import logging
import threading
import time

from src.core.query_engine.dag.dag import DAG
from src.core.query_engine.query_execution.sequential_execution import SequentialExecutionStrategy


class QueryExecutor:
    def __init__(self, memory_layers, strategy=None):
        """
        Initialize the query executor with a specific execution strategy.
        :param memory_layers: Memory layers available for queries.
        :param strategy: Execution strategy (default is SequentialExecutionStrategy).
        """
        self.memory_layers = memory_layers
        self.strategy = strategy or SequentialExecutionStrategy()
        self.continuous_queries = []

    def set_strategy(self, strategy):
        """
        Set the execution strategy.
        :param strategy: Instance of an execution strategy.
        """
        self.strategy = strategy

    def execute(self, dag: DAG) -> dict:
        """
        Execute a one-shot query using the selected strategy.
        :param dag: Optimized DAG to execute.
        :return: Final result from the DAG execution.
        """
        return self.strategy.execute(dag)

    def register_continuous_query(self, dag, interval=10):
        """
        Register a continuous query by creating a new thread.
        :param dag: DAG representing the continuous query.
        :param interval: Time interval in seconds for periodic execution.
        """
        query_thread = threading.Thread(target=self._execute_continuously, args=(dag, interval))
        query_thread.daemon = True
        query_thread.start()
        self.continuous_queries.append(query_thread)

    def _execute_continuously(self, dag, interval):
        """
        Continuously execute a DAG at the specified interval.
        :param dag: The DAG to execute.
        :param interval: Time interval between executions.
        """
        while True:
            try:
                logging.info(f"Executing continuous query: {dag}")
                self.execute(dag)
            except Exception as e:
                logging.error(f"Error in continuous query execution: {str(e)}")
            time.sleep(interval)
