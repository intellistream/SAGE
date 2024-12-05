# src/core/query_engine/query_executor.py
import logging
import threading
import time

class QueryExecutor:
    def __init__(self, memory_layers):
        self.memory_layers = memory_layers
        self.continuous_queries = []

    def execute(self, dag):
        """
        Execute a one-shot query by running the DAG nodes sequentially.
        :param dag: Optimized DAG to execute.
        :return: Final result from the DAG execution.
        """
        results = {}
        for node in dag.nodes:
            result = node.execute()
            results[node.operator_name] = result
        return results

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
